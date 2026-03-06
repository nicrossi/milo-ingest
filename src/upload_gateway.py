import json
import logging
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import boto3
import cgi
import psycopg2
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("UPLOAD_GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("UPLOAD_GATEWAY_PORT", "8010"))
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
INGEST_BUCKET = os.getenv("INGEST_BUCKET", "milo-raw-ingest-local")
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "uploads")
ALLOW_ORIGIN = os.getenv("UPLOAD_GATEWAY_ALLOW_ORIGIN", "http://localhost:3000")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
DB_URL = os.getenv("DB_URL", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("upload-gateway")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION,
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def safe_name(filename: str) -> str:
    name = filename.strip().replace("\\", "/").split("/")[-1]
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:180] or "upload.bin"


def get_embedding_count(source_file: str) -> int:
    if not DB_URL:
        return 0
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM document_embeddings WHERE source_file = %s",
                (source_file,),
            )
            return int(cur.fetchone()[0] or 0)
    finally:
        conn.close()


def wait_for_embedding(source_file: str, timeout_sec: int = 120, poll_sec: float = 1.5) -> int:
    deadline = time.time() + max(1, timeout_sec)
    while time.time() < deadline:
        count = get_embedding_count(source_file)
        if count > 0:
            return count
        time.sleep(poll_sec)
    return get_embedding_count(source_file)


class UploadHandler(BaseHTTPRequestHandler):
    def _write_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(200, {"ok": True, "bucket": INGEST_BUCKET})
            return
        if parsed.path == "/ingest-status":
            params = parse_qs(parsed.query or "")
            key = (params.get("key") or [""])[0]
            if not key:
                self._write_json(400, {"detail": "Missing query param: key"})
                return
            if not DB_URL:
                self._write_json(500, {"detail": "DB_URL not configured in upload gateway"})
                return
            count = get_embedding_count(key)
            self._write_json(200, {"ok": True, "key": key, "ready": count > 0, "count": count})
            return
        self._write_json(404, {"detail": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/upload":
            self._write_json(404, {"detail": "Not Found"})
            return
        params = parse_qs(parsed.query or "")
        wait_enabled = (params.get("wait_for_embedding") or ["0"])[0].lower() in {"1", "true", "yes"}
        timeout_sec = int((params.get("timeout_sec") or ["120"])[0])

        ctype = self.headers.get("content-type", "")
        if "multipart/form-data" not in ctype:
            self._write_json(400, {"detail": "Expected multipart/form-data"})
            return

        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": ctype,
            "CONTENT_LENGTH": self.headers.get("content-length", "0"),
        }

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ=environ,
                keep_blank_values=True,
            )
            file_item = form["file"] if "file" in form else None
            session_id = form.getvalue("session_id", "default")
            if file_item is None or getattr(file_item, "file", None) is None:
                self._write_json(400, {"detail": "Missing form field: file"})
                return

            original_name = safe_name(file_item.filename or "upload.bin")
            session_segment = re.sub(r"[^a-zA-Z0-9._-]", "_", str(session_id))[:80] or "default"
            object_key = f"{UPLOAD_PREFIX}/{session_segment}/{int(time.time() * 1000)}_{original_name}"
            data = file_item.file.read()

            s3.upload_fileobj(
                Fileobj=BytesIO(data),
                Bucket=INGEST_BUCKET,
                Key=object_key,
                ExtraArgs={"ContentType": file_item.type or "application/octet-stream"},
            )
            logger.info("Uploaded to s3://%s/%s (%s bytes)", INGEST_BUCKET, object_key, len(data))

            if SQS_QUEUE_URL:
                body = {
                    "Records": [
                        {
                            "eventSource": "aws:s3",
                            "eventName": "ObjectCreated:Put",
                            "awsRegion": AWS_REGION,
                            "eventTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "s3": {
                                "bucket": {"name": INGEST_BUCKET},
                                "object": {"key": object_key, "size": len(data)},
                            },
                        }
                    ]
                }
                sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(body))
                logger.info("Published ingest event to SQS: %s", SQS_QUEUE_URL)

            embedding_count = 0
            ready = False
            if wait_enabled:
                if not DB_URL:
                    self._write_json(500, {"detail": "wait_for_embedding requires DB_URL in upload gateway"})
                    return
                logger.info("Waiting for embedding row for key=%s (timeout=%ss)", object_key, timeout_sec)
                embedding_count = wait_for_embedding(object_key, timeout_sec=timeout_sec)
                ready = embedding_count > 0

            self._write_json(
                200,
                {
                    "ok": True,
                    "bucket": INGEST_BUCKET,
                    "key": object_key,
                    "filename": original_name,
                    "size": len(data),
                    "ready": ready,
                    "embedding_count": embedding_count,
                },
            )
        except Exception as exc:
            self._write_json(500, {"detail": f"Upload failed: {exc}"})


def main():
    server = ThreadingHTTPServer((HOST, PORT), UploadHandler)
    logger.info(
        "Upload gateway listening on http://%s:%s (bucket=%s, sqs=%s)",
        HOST,
        PORT,
        INGEST_BUCKET,
        SQS_QUEUE_URL or "<disabled>",
    )
    server.serve_forever()


if __name__ == "__main__":
    main()

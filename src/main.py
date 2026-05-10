import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from urllib.parse import unquote_plus

import boto3
from dotenv import load_dotenv

from parser import DocumentParser
from embedder import ContentEmbedder
from store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("milo-ingest-main")

load_dotenv()

ENV = os.getenv("ENV", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") if ENV == "local" else None
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
DB_NAME = os.getenv("DB_NAME")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_URL = os.getenv("DB_URL") if ENV != "local" else f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@localhost:5433/{DB_NAME}"
HEALTH_FILE = "/tmp/worker.ready"

if not SQS_QUEUE_URL or not DB_URL:
    raise ValueError("Missing required environment variables: SQS_QUEUE_URL or DB_URL")

sqs_client = boto3.client("sqs", region_name=AWS_REGION, endpoint_url=ENDPOINT_URL)
s3_client = boto3.client("s3", region_name=AWS_REGION, endpoint_url=ENDPOINT_URL)

doc_parser = DocumentParser()
embedder = ContentEmbedder()
vector_store = VectorStore(DB_URL)

def shutdown_handler(signum, frame):
    logger.info("Shutdown signal received. Closing resources.")
    vector_store.close()
    try:
        Path(HEALTH_FILE).unlink(missing_ok=True)
    except OSError:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

def process_file(bucket: str, object_key: str):
    local_path = Path(f"/tmp/{object_key}")
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Fetch S3 object metadata
        head_response = s3_client.head_object(Bucket=bucket, Key=object_key)
        metadata = head_response.get('Metadata', {})
        activity_id = metadata.get('activity_id') or metadata.get('activity-id')

        s3_client.download_file(bucket, object_key, str(local_path))
        markdown = doc_parser.parse_to_markdown(local_path)
        chunks = embedder.chunk_text(markdown)

        if not chunks:
            logger.warning("No text content found in %s", object_key)
            return

        vectors = embedder.embed_chunks(chunks)
        vector_store.save_vectors(object_key, chunks, vectors, activity_id=activity_id)
    finally:
        if local_path.exists():
            local_path.unlink()

def delete_file(object_key: str):
    vector_store.delete_vectors(object_key)

def process_message(message: dict):
    body = json.loads(message["Body"])

    if "Records" in body:
        for record in body["Records"]:
            event_name = record.get("eventName", "")
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])

            try:
                if event_name.startswith("ObjectCreated"):
                    logger.info("Processing s3://%s/%s", bucket, key)
                    process_file(bucket, key)
                elif event_name.startswith("ObjectRemoved"):
                    logger.info("Deleting embeddings for s3://%s/%s", bucket, key)
                    delete_file(key)
                else:
                    logger.warning("Unhandled eventName=%s for s3://%s/%s",
                                   event_name, bucket, key)
                    continue
            except Exception as e:
                # SQS visibility timeout will expire,
                # and the message will be retried or sent to DLQ.
                logger.error("Failed %s for s3://%s/%s: %s",
                             event_name, bucket, key, e, exc_info=True)
                return

    sqs_client.delete_message(
        QueueUrl=SQS_QUEUE_URL,
        ReceiptHandle=message["ReceiptHandle"]
    )
    logger.info("Successfully processed and deleted message from queue.")

def poll_queue():
    logger.info("Worker started. Listening on: %s", SQS_QUEUE_URL)
    try:
        with open(HEALTH_FILE, "w") as f:
            f.write("ready")
        logger.info("Health sentinel written to %s", HEALTH_FILE)
    except OSError as e:
        logger.warning("Could not write health sentinel: %s", e)

    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            for message in response.get("Messages", []):
                process_message(message)
        except Exception as e:
            logger.error("Worker execution failed: %s", e, exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    poll_queue()
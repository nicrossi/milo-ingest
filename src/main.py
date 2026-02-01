import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import unquote_plus

import boto3
from dotenv import load_dotenv

from parser import DocumentParser

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

sqs_client = boto3.client("sqs", region_name=AWS_REGION, endpoint_url=ENDPOINT_URL)
s3_client = boto3.client("s3", region_name=AWS_REGION, endpoint_url=ENDPOINT_URL)
doc_parser = DocumentParser()

def download_and_parse(bucket_name: str, object_key: str) -> str:
    """Download S3 object and parse to markdown."""
    local_path = Path(f"/tmp/{object_key}")
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        s3_client.download_file(bucket_name, object_key, str(local_path))
        markdown = doc_parser.parse_to_markdown(local_path)
        logger.info(f"Parsed {len(markdown)} characters of markdown")
        return markdown
    finally:
        # Clean up temporary file
        if local_path.exists():
            local_path.unlink()

def process_message(message):
    body = json.loads(message["Body"])

    if "Records" in body:
        for record in body["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = unquote_plus(record["s3"]["object"]["key"])
            logger.info(f"File detected: s3://{bucket_name}/{object_key}")

            markdown = download_and_parse(bucket_name, object_key)

    sqs_client.delete_message(
        QueueUrl=SQS_QUEUE_URL,
        ReceiptHandle=message["ReceiptHandle"]
    )

def poll_queue():
    logger.info(f"Worker started. Listening on: {SQS_QUEUE_URL}")

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
            logger.error(f"Worker encountered an error: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    poll_queue()

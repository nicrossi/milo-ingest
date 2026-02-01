import json
import logging
import os
import time
from urllib.parse import unquote_plus

import boto3
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("docling-ack")

load_dotenv()

ENV = os.getenv("ENV", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") if ENV == "local" else None
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

sqs_client = boto3.client("sqs", region_name=AWS_REGION, endpoint_url=ENDPOINT_URL)

def process_message(message):
    body = json.loads(message["Body"])

    if "Records" in body:
        for record in body["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = unquote_plus(record["s3"]["object"]["key"])
            logger.info(f"File detected: s3://{bucket_name}/{object_key}")

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

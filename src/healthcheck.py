"""
Healthcheck script for ECS container readiness verification.

ECS uses this to determine if the essential container is alive.
See: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-event-messages-list.html#service-event-messages-1

Exits 0  → healthy (container is running and core imports are functional)
Exits 1  → unhealthy (ECS will restart the task)
"""
import sys
import os

HEALTH_FILE = "/tmp/worker.ready"

try:
    # Verify the worker has signalled readiness via the sentinel file
    if not os.path.exists(HEALTH_FILE):
        print("UNHEALTHY: worker readiness file not found", flush=True)
        sys.exit(1)

    import boto3
    import psycopg2
    import sentence_transformers

    print("HEALTHY", flush=True)
    sys.exit(0)
except Exception as e:
    print(f"UNHEALTHY: {e}", flush=True)
    sys.exit(1)


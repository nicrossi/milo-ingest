# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install minimal system deps needed at build time (and for some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libxrandr2 \
    libxinerama1 \
    libxi6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Final
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install runtime system libs required by OpenCV/docling and friends
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libxrandr2 \
    libxinerama1 \
    libxi6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY src/ /app/src/

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# ECS health check: verifies the essential container is alive.
# start_period gives the worker time to initialise before failures count.
# See: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-event-messages-list.html#service-event-messages-1
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/src/healthcheck.py

CMD ["python", "src/main.py"]

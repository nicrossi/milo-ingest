resource "aws_sqs_queue" "this" {
  name                      = "milo-ingest-${var.environment}"
  delay_seconds             = 0
  message_retention_seconds = 86400 # 1 day
  receive_wait_time_seconds = 20    # Long Polling

  # DLQ config
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "dlq" {
  name = "milo-ingest-dlq-${var.environment}"
}

# Allows S3 to send messages to this SQS queue
resource "aws_sqs_queue_policy" "this" {
  queue_url = aws_sqs_queue.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.this.arn
        Condition = {
          ArnEquals = { "aws:SourceArn" = var.bucket_arn }
        }
      }
    ]
  })
}

# Trigger: S3 ObjectCreated
resource "aws_s3_bucket_notification" "this" {
  bucket = var.bucket_id

  queue {
    queue_arn     = aws_sqs_queue.this.arn
    events        = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_sqs_queue_policy.this]
}

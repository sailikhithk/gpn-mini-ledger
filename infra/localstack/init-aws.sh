#!/bin/bash
# LocalStack initialization - provisions AWS resources locally
# Runs automatically when LocalStack container starts

set -e

echo "[gpn] Provisioning LocalStack resources..."

# S3 bucket for audit log cold storage (CDN-style static hosting)
awslocal s3 mb s3://gpn-audit-archive
awslocal s3api put-bucket-versioning \
  --bucket gpn-audit-archive \
  --versioning-configuration Status=Enabled

# S3 bucket for OpenAPI docs (CDN-served static content)
awslocal s3 mb s3://gpn-public-docs
awslocal s3 website s3://gpn-public-docs \
  --index-document index.html \
  --error-document 404.html

# SQS queue for webhook dead-letter queue
awslocal sqs create-queue \
  --queue-name gpn-webhook-dlq

# SQS queue for reconciliation cases
awslocal sqs create-queue \
  --queue-name gpn-reconciliation-queue

# DynamoDB table for idempotency (alternative to Postgres)
awslocal dynamodb create-table \
  --table-name gpn-idempotency \
  --attribute-definitions AttributeName=key,AttributeType=S \
  --key-schema AttributeName=key,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# DynamoDB table for webhook delivery tracking
awslocal dynamodb create-table \
  --table-name gpn-webhook-deliveries \
  --attribute-definitions AttributeName=event_id,AttributeType=S \
  --key-schema AttributeName=event_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Secrets Manager - HMAC signing key for webhooks
awslocal secretsmanager create-secret \
  --name gpn/webhook/hmac-key \
  --secret-string '{"key":"gpn-local-dev-hmac-key-do-not-use-in-production","algorithm":"HmacSHA256"}'

# Secrets Manager - fraud engine API key
awslocal secretsmanager create-secret \
  --name gpn/fraud/api-key \
  --secret-string '{"key":"gpn-local-dev-fraud-key"}'

# Kinesis stream for event streaming (alternative to Redpanda)
awslocal kinesis create-stream \
  --stream-name gpn-payment-events \
  --shard-count 1

echo "[gpn] LocalStack resources provisioned successfully."
echo "[gpn]   S3: gpn-audit-archive, gpn-public-docs"
echo "[gpn]   SQS: gpn-webhook-dlq, gpn-reconciliation-queue"
echo "[gpn]   DynamoDB: gpn-idempotency, gpn-webhook-deliveries"
echo "[gpn]   Secrets: gpn/webhook/hmac-key, gpn/fraud/api-key"
echo "[gpn]   Kinesis: gpn-payment-events"

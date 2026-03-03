#!/usr/bin/env bash
# Deploy script for SafeACS Phase 5
# Automates the build and push of the unified React/FastAPI container to Google Cloud Run

set -e

PROJECT_ID="gen-lang-client-0364391286"
SERVICE_NAME="safe-acs"
REGION="us-central1"

echo "=========================================================="
echo "🚀 Deploying SafeACS Mission Control to Google Cloud Run"
echo "Project: $PROJECT_ID | Service: $SERVICE_NAME"
echo "=========================================================="

echo "[1/2] Authenticating and configuring gcloud..."
gcloud config set project $PROJECT_ID

echo "[2/2] Triggering Cloud Run deploy from source..."
# Note: This will build the multi-stage Dockerfile via Cloud Build remotely 
# and automatically route 100% of traffic to the new revision.

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --timeout 300 \
  --set-env-vars ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

echo "=========================================================="
echo "✅ Deployment Complete!"
echo "If you provided an ANTHROPIC_API_KEY, the Claude Cognitive Layer is active."
echo "=========================================================="

#!/usr/bin/env bash
# Deploy the authenticated gateway. Never rewrites tracked files.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
: "${PROJECT_ID:=${GOOGLE_CLOUD_PROJECT:-}}"
: "${REGION:=us-central1}"
: "${SERVICE_NAME:=central-market-relief}"
: "${SERVICE_ACCOUNT:?Set SERVICE_ACCOUNT to the dedicated runtime service account email}"
: "${API_TOKEN_SECRET:?Set API_TOKEN_SECRET to an existing Secret Manager secret containing the officer access token}"
: "${EVIDENCE_GCS_BUCKET:?Set EVIDENCE_GCS_BUCKET to an existing private versioned Cloud Storage bucket}"
if [[ -z "$PROJECT_ID" ]]; then
  echo 'Set PROJECT_ID or GOOGLE_CLOUD_PROJECT explicitly.' >&2
  exit 1
fi
# Private Cloud Run access plus an application token. Provision the account, secret,
# private versioned evidence bucket separately; this script does not grant broad IAM roles.
gcloud run deploy "$SERVICE_NAME" \
  --source "$REPO_ROOT" \
  --project "$PROJECT_ID" --region "$REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --no-allow-unauthenticated \
  --memory 2Gi --cpu 1 --max-instances 3 --concurrency 8 \
  --set-secrets "RELIEF_API_TOKEN=${API_TOKEN_SECRET}:latest" \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BQ_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},BQ_DATASET=a4i_econ,REGION=${REGION},AGENT_RUNTIME_RESOURCE=${AGENT_RUNTIME_RESOURCE:-},EVIDENCE_GCS_BUCKET=${EVIDENCE_GCS_BUCKET}"

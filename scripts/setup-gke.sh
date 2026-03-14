#!/bin/bash
# Run this once to provision the GKE cluster and supporting infra.
# Usage: GCP_PROJECT=my-project ./scripts/setup-gke.sh

set -euo pipefail

PROJECT=${GCP_PROJECT:?Set GCP_PROJECT env var}
CLUSTER=kitchen-planner-cluster
ZONE=asia-south1-a       # Mumbai — closest to Pune
REGION=asia-south1

echo ">>> Setting project"
gcloud config set project "$PROJECT"

echo ">>> Enabling APIs"
gcloud services enable \
  container.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com

echo ">>> Creating GKE Autopilot cluster (handles node scaling automatically)"
gcloud container clusters create-auto "$CLUSTER" \
  --region "$REGION" \
  --release-channel regular

echo ">>> Getting credentials"
gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"

echo ">>> Reserving static IP for Ingress"
gcloud compute addresses create kitchen-planner-ip --global

echo ">>> Creating namespace"
kubectl create namespace kitchen-planner --dry-run=client -o yaml | kubectl apply -f -

echo ">>> Creating secrets (fill in real values first!)"
kubectl create secret generic kitchen-planner-secrets \
  --namespace kitchen-planner \
  --from-literal=ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:?}" \
  --from-literal=SUPABASE_URL="https://cfcviixmuchtzynetphq.supabase.co" \
  --from-literal=SUPABASE_KEY="${SUPABASE_KEY:?}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ">>> Connecting Cloud Build to repo (do this in GCP Console)"
echo "    https://console.cloud.google.com/cloud-build/triggers"
echo ""
echo ">>> Done! Update k8s/base/ingress.yaml with your real domain, then run:"
echo "    kubectl apply -k k8s/overlays/prod"

# AI Kitchen Planner — Microservices on GKE

Production-ready microservices architecture for generating daily vegetarian meal plans in Hindi, deployed on Google Kubernetes Engine.

## Services

| Service | Port | Responsibility |
|---------|------|----------------|
| `api-gateway` | 8000 | Entry point — routing, CORS |
| `household-service` | 8001 | Profiles, ingredients, preferences, context |
| `planner-service` | 8002 | Claude AI orchestration, plan generation, Redis cache |
| `translation-service` | 8003 | Hindi NLG via Claude |
| `feedback-service` | 8004 | Ratings, history queries |
| `scheduler-service` | — | GKE CronJob — 6 AM IST pre-generation |

## Prerequisites

- Google Cloud SDK (`gcloud`)
- `kubectl`
- `kustomize`
- Docker
- A GCP project with billing enabled

## Quick Start — Local Dev

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY and SUPABASE_KEY
./scripts/dev.sh              # starts all services via docker-compose
# API available at http://localhost:8000
```

## GKE Deployment

### 1. Provision cluster (one-time)
```bash
export GCP_PROJECT=your-project-id
export ANTHROPIC_API_KEY=sk-ant-...
export SUPABASE_KEY=eyJ...
./scripts/setup-gke.sh
```

### 2. Update configuration
- Set your domain in `k8s/base/ingress.yaml` and `k8s/base/managed-cert.yaml`
- Set your GCP Project ID in `k8s/overlays/prod/kustomization.yaml`

### 3. Build and push images manually (or use Cloud Build)
```bash
export PROJECT=your-project-id
for svc in api-gateway household-service planner-service translation-service feedback-service scheduler-service; do
  docker build -t gcr.io/$PROJECT/$svc:prod ./services/$svc
  docker push gcr.io/$PROJECT/$svc:prod
done
```

### 4. Deploy
```bash
kubectl apply -k k8s/overlays/prod
kubectl rollout status deployment -n kitchen-planner
```

### 5. CI/CD via Cloud Build (recommended)
Connect your repo to Cloud Build — every push to `main` automatically builds, pushes, and deploys.

```bash
# Connect in Cloud Build console, then trigger is created automatically
# Manually trigger:
gcloud builds submit --config cloudbuild.yaml
```

## Project Structure

```
kitchen-planner-k8s/
├── services/
│   ├── api-gateway/            # Reverse proxy (port 8000)
│   ├── household-service/      # Profiles & pantry (port 8001)
│   ├── planner-service/        # Claude AI + Redis (port 8002)
│   ├── translation-service/    # Hindi NLG (port 8003)
│   ├── feedback-service/       # Ratings & history (port 8004)
│   └── scheduler-service/      # CronJob runner
├── k8s/
│   ├── base/                   # All K8s manifests
│   └── overlays/
│       ├── dev/                # 1 replica, dev tags
│       └── prod/               # 3 replicas, prod tags, HPA
├── scripts/
│   ├── setup-gke.sh            # One-time cluster setup
│   └── dev.sh                  # Local docker-compose runner
├── cloudbuild.yaml             # Cloud Build CI/CD pipeline
└── docker-compose.yml          # Local development
```

## Architecture Decisions

- **API Gateway pattern** — all client traffic enters via one service; internal services are unreachable from outside (ClusterIP only)
- **Redis cache** — today's meal plans cached for 24h; repeated mobile loads are instant
- **GKE CronJob** — scheduler runs at 00:30 UTC (6 AM IST) so plans are ready before breakfast
- **Kustomize overlays** — same base manifests, different resource levels for dev vs prod
- **HPA on planner + gateway** — Claude calls are bursty; auto-scale pods 2→8 on CPU pressure
- **Supabase in Mumbai (ap-south-1)** — co-located with GKE cluster in asia-south1 for low latency

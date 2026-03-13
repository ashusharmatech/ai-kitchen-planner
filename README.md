# AI Kitchen Planner 🍳

Microservices system that generates daily **vegetarian meal plans in Hindi** using OpenAI GPT-4o-mini.
Deployed on **Render.com** (free tier). Frontend on **GitHub Pages**.

## Live URLs
| What | URL |
|---|---|
| Cook UI (Hindi) | https://ashusharmatech.github.io/ai-kitchen-planner/ |
| API Gateway | https://kitchen-api-gateway.onrender.com |

## Services

| Service | Port | Responsibility |
|---|---|---|
| `api-gateway` | 8000 | Single entry point — routing, CORS |
| `household-service` | 8001 | Profiles, ingredients, preferences, context |
| `planner-service` | 8002 | OpenAI GPT-4o-mini — plan generation + Redis cache |
| `translation-service` | 8003 | Hindi NLG via OpenAI |
| `feedback-service` | 8004 | Ratings and history |
| `scheduler-service` | — | Render Cron — 6 AM IST daily pre-generation |

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11 + FastAPI |
| AI | OpenAI GPT-4o-mini |
| Database | Supabase (Postgres + RLS) — Mumbai region |
| Cache | Redis (Render free tier) |
| Cook UI | Vanilla HTML — Hindi, mobile-first |
| Admin UI | Vanilla HTML — English, desktop |
| Hosting | Render.com (backend) + GitHub Pages (frontend) |
| CI/CD | GitHub Actions |

## Local Development

```bash
cp .env.example .env          # add OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY
./scripts/dev.sh              # docker-compose up --build
# API at http://localhost:8000
# Cook UI: open frontend/index.html
```

## Render Deployment

1. Go to [render.com](https://render.com) → New → **Blueprint**
2. Connect this GitHub repo — Render reads `render.yaml` automatically
3. In Render dashboard set environment variables for each service:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. Deploy — all 7 services (5 web + 1 Redis + 1 cron) are created

Every `git push` to `main` triggers an auto-redeploy on Render.

## GitHub Secrets Required

Add these in: repo → Settings → Secrets and variables → Actions

| Secret | Value |
|---|---|
| `OPENAI_API_KEY` | From platform.openai.com |
| `SUPABASE_URL` | `https://cfcviixmuchtzynetphq.supabase.co` |
| `SUPABASE_KEY` | From Supabase dashboard → Project Settings → API |

## GitHub Pages Setup (one-time)

Repo → Settings → Pages → Source: **GitHub Actions**

The `deploy-frontend.yml` workflow publishes `frontend/` automatically on every push.

## Project Structure

```
ai-kitchen-planner/
├── .github/
│   ├── workflows/
│   │   ├── deploy-frontend.yml   # Auto-deploy to GitHub Pages on push
│   │   └── test-services.yml     # Lint + Docker build on PRs
│   └── SECRETS.md                # Which secrets to add and where
├── frontend/
│   ├── index.html                # Cook-facing Hindi UI (mobile)
│   └── admin.html                # Admin panel (desktop)
├── services/
│   ├── api-gateway/              # Port 8000 — reverse proxy
│   ├── household-service/        # Port 8001 — pantry & profiles
│   ├── planner-service/          # Port 8002 — OpenAI + Redis
│   ├── translation-service/      # Port 8003 — Hindi NLG
│   ├── feedback-service/         # Port 8004 — ratings & history
│   └── scheduler-service/        # Cron — 6 AM IST
├── k8s/                          # Kubernetes manifests (GKE path)
├── render.yaml                   # Render Blueprint (active deployment)
├── docker-compose.yml            # Local dev
└── .env.example                  # Environment variable template
```

## Cost

| Service | Cost |
|---|---|
| Render (all services + Redis + cron) | Free |
| Supabase (Postgres) | Free |
| GitHub (repo + Actions + Pages) | Free |
| OpenAI API (~120 calls/month) | ~₹30/month |

**Total: ~₹30/month for one household.**

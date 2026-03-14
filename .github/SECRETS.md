# GitHub Secrets Setup

Go to: your repo → Settings → Secrets and variables → Actions → New repository secret

Add these three secrets:

| Secret name       | Where to get it                              |
|-------------------|----------------------------------------------|
| `OPENAI_API_KEY`  | platform.openai.com → API Keys               |
| `SUPABASE_URL`    | https://cfcviixmuchtzynetphq.supabase.co     |
| `SUPABASE_KEY`    | Supabase dashboard → Project Settings → API  |

These are used by the GitHub Actions CI workflow to build and test Docker images.
They are NEVER stored in the repo files — only in GitHub's encrypted secrets vault.

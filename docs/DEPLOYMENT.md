# Deploying Harmonia (future steps — nothing here has been executed)

Harmonia is two deployables: a Python API (needs ~400 MB RAM for the 57,650 × 5,000
sparse TF-IDF matrix plus pandas) and a static-ish Next.js app. Deploy the API first,
then point the frontend at it.

## 1. Push to GitHub

```bash
cd Harmonia_Music_Recommender
git init
git add .
git commit -m "Harmonia music recommender"
git branch -M main
git remote add origin git@github.com:<you>/harmonia.git
git push -u origin main
```

`artifacts/`, `node_modules/`, `.next/` and `.env*` are ignored. The 75 MB CSV is
committed as a plain file (under GitHub's 100 MB limit). If you prefer not to commit
it, add `data/*.csv` to `.gitignore`, host the file elsewhere, and set
`HARMONIA_DATA_PATH` on the server (or download it in a build step).

## 2. Backend on Render (or Railway / Fly.io / a VPS)

Render → New → Web Service → connect the repo.

| Setting        | Value |
| -------------- | ----- |
| Root directory | `.` (repository root) |
| Runtime        | Python 3.12 |
| Build command  | `pip install -r backend/requirements.txt && python scripts/prepare_data.py` |
| Start command  | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| Instance       | at least 512 MB RAM |

Environment variables:

```
HARMONIA_CORS_ORIGINS=https://<your-vercel-app>.vercel.app
HARMONIA_BUILD_ON_STARTUP=true
```

Building artifacts in the build step means the first request is fast; with
`HARMONIA_BUILD_ON_STARTUP=true` the server also self-heals if the artifacts are missing.
Health check path: `/health` (returns `"ready": true` once the matrix is loaded).

A `render.yaml` blueprint is included at the repository root as a starting point.

### Docker (any host)

```bash
docker build -t harmonia-api -f backend/Dockerfile .
docker run -p 8000:8000 -e HARMONIA_CORS_ORIGINS=https://your-frontend.example harmonia-api
```

## 3. Frontend on Vercel

Vercel → Add New → Project → import the repo.

| Setting          | Value |
| ---------------- | ----- |
| Framework preset | Next.js |
| Root directory   | `frontend` |
| Build command    | `npm run build` (default) |

Environment variable (Production + Preview):

```
NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com
```

Because `NEXT_PUBLIC_*` values are inlined at build time, redeploy the frontend after
changing it. Then add the Vercel URL to `HARMONIA_CORS_ORIGINS` on the backend.

## 4. Checklist after deploy

- `GET https://<api>/health` → `{"status":"ok","ready":true,"songs":57650}`
- Open the Vercel URL; header shows "Engine ready".
- Search "Dancing Queen" → seed `S00011`, first recommendation `S00074 Reina Danzante`.

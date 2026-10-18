# TraceOps AI — Cloud Deployment Guide (Render + Vercel + FalkorDB Cloud)

This guide walks you through deploying **TraceOps AI** using the split cloud architecture:
* **Graph Database**: Managed [FalkorDB Cloud](https://app.falkordb.cloud/) (Free tier available)
* **Backend API**: [Render](https://render.com/) (FastAPI REST service)
* **Frontend Dashboard**: [Vercel](https://vercel.com/) (React + Vite + Cytoscape SPA)

```text
 ┌────────────────────────┐         ┌────────────────────────┐
 │        Vercel          │  HTTPS  │         Render         │
 │ React + Vite Dashboard │ ──────> │    FastAPI REST API    │
 └────────────────────────┘         └───────────┬────────────┘
                                                │ Redis TLS
                                                ▼
                                    ┌────────────────────────┐
                                    │     FalkorDB Cloud     │
                                    │  Managed Graph Cluster │
                                    └────────────────────────┘
```

---

## Step 1: Create a Managed FalkorDB Cloud Database

1. Sign up or log in to the [FalkorDB Cloud Console](https://app.falkordb.cloud/).
2. Click **Create Database** (select the free tier).
3. Once provisioned, note down your connection credentials:
   * **Host**: e.g., `db-xxxx.falkordb.cloud`
   * **Port**: usually `6379`
   * **Username**: `default`
   * **Password**: your instance password
   * **SSL / TLS**: Enabled (`true`)

---

## Step 2: Deploy the FastAPI Backend to Render

1. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New +** > **Web Service**.
2. Connect your GitHub repository: `https://github.com/umeshsatpathi/TraceOps-AI`.
3. Configure the service settings:
   * **Name**: `traceops-ai-backend`
   * **Region**: Choose the region closest to your FalkorDB instance.
   * **Branch**: `main`
   * **Root Directory**: *(Leave blank - repo root)*
   * **Runtime**: **Python 3**
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Add the following **Environment Variables**:

| Variable | Recommended Value | Description |
|---|---|---|
| `FALKORDB_HOST` | `db-xxxx.falkordb.cloud` | FalkorDB Cloud endpoint |
| `FALKORDB_PORT` | `6379` | Database port |
| `FALKORDB_GRAPH` | `traceshield` | Graph identifier |
| `FALKORDB_USERNAME` | `default` | Database user |
| `FALKORDB_PASSWORD` | `your_cloud_password` | Cloud instance secret |
| `FALKORDB_SSL` | `true` | Secure TLS connection |
| `GOOGLE_API_KEY` | `your_gemini_api_key` | Gemini AI API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Gemini model name |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Allowed frontend URL(s) |

5. Click **Create Web Service**.
6. Once deployed, verify your backend is live by visiting:
   * `https://<your-backend>.onrender.com/api/health`
   * `https://<your-backend>.onrender.com/api/docs` (Swagger UI)

---

## Step 3: Deploy the React Frontend to Vercel

1. Log in to [Vercel](https://vercel.com/) and click **Add New...** > **Project**.
2. Select your repository `umeshsatpathi/TraceOps-AI`.
3. Configure Project Settings:
   * **Framework Preset**: `Vite` (automatically detected)
   * **Root Directory**: Click *Edit* and select **`frontend`**
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
4. Add the **Environment Variable**:

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://<your-backend>.onrender.com/api` |

5. Click **Deploy**.
6. Vercel will build the frontend and provide your live URL (e.g. `https://traceops-ai.vercel.app`).
   * *Note: The repository already includes `frontend/vercel.json` so client-side SPA routing (`/findings`, `/graph`, `/investigations`) works without 404 errors on page refresh.*

---

## Step 4: Seed the Cloud Graph Database

The FastAPI backend automatically executes idempotent graph seeding on startup (`startup_seed`), so once your backend connects to FalkorDB Cloud, the initial nodes (`F-001`, `F-002`, `ep-orders`, `customer-orders`, etc.) are created automatically.

If you ever want to re-seed or run seeding manually from your local terminal against your cloud database:

```bash
# Windows PowerShell:
$env:FALKORDB_HOST="db-xxxx.falkordb.cloud"
$env:FALKORDB_PORT="6379"
$env:FALKORDB_PASSWORD="your_cloud_password"
$env:FALKORDB_SSL="true"
$env:FALKORDB_GRAPH="traceshield"
python seed_graph.py
python seed_operational_context.py
```

---

## Step 5: Verification & End-to-End Testing

1. Open your live Vercel dashboard: `https://your-app.vercel.app`.
2. Check the **System Status** indicator in the navbar: should show **Backend: Online** and **FalkorDB: Online**.
3. Navigate to **Findings**: Verify finding `F-001` (BOLA) and `F-002` (Missing CSP) are visible.
4. Navigate to **Attack Graph**: Click on `ep-orders` and inspect the Cytoscape attack path topology.
5. Navigate to **AI Investigations**: Ask a question or run an investigation on `F-001` to test the Gemini agent integration.

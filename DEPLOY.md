# Deploying Reviva

Reviva is one process: FastAPI serves both the `/api` endpoints and the built
React UI. So there is nothing to split — one host, one URL.

The catch is weight: PyTorch + Real-ESRGAN + GFPGAN need roughly 2 GB of RAM
just to load. That rules out most free tiers (Render, Railway, Back4App and
friends cap a free container at 256–512 MB) and all serverless function
platforms (Vercel and Netlify cap a function bundle at ~250 MB, so PyTorch
never fits). Pick from the options below instead.

| Option | Cost | Card needed | GPU | Video | Good for |
|---|---|---|---|---|---|
| Hugging Face Space (CPU basic) | free | no | no | 3 s clips | a public demo |
| Google Cloud Run | free tier | yes | no | short clips | a real deployment |
| Oracle Cloud Always Free VM | free | yes | no | yes | always-on self-host |
| Your own machine / GPU box | — | — | yes | yes | full speed |

---

## Option 1 — Hugging Face Space (free, no credit card)

Docker Spaces now require a paid plan, so Reviva ships a Gradio-SDK entrypoint
(`deploy/space/app.py`) that still serves the real app:

- `/` — the React UI
- `/gradio` — a minimal Gradio UI, plus a free auto-generated API
- `/api/enhance/photo` — the FastAPI endpoint
- `/health`

Free hardware is **CPU basic: 2 vCPU, 16 GB RAM, 50 GB non-persistent disk**.
It sleeps when idle and wakes on the next request.

### Steps

1. **Create the Space.** On huggingface.co: *New* → *Space*. Name it `reviva`,
   SDK **Gradio**, hardware **CPU basic (free)**, visibility **Public**
   (private Spaces are not free).

2. **Get an access token** with *write* permission:
   Settings → Access Tokens → *New token*.

3. **Assemble the deployable folder** (builds the React UI, then copies
   `backend/`, the build and the Space files into `.space-build/`):

   ```powershell
   powershell -File deploy\build-space.ps1
   ```

4. **Push it** (first time only):

   ```powershell
   cd .space-build
   git init -b main
   git remote add origin https://huggingface.co/spaces/<your-hf-username>/reviva
   git add -A
   git commit -m "deploy Reviva"
   git push -u origin main --force
   ```

   Username = your HF name, password = the token from step 2. `--force` is
   needed only on this first push: creating the Space already made a starter
   commit on the remote, and this replaces it.

5. Watch the **Logs** tab. The first build takes 5–10 minutes (PyTorch is
   large). When it says the app is running, open the Space URL.

6. **Later updates:** re-run step 3, then inside `.space-build`:
   `git add -A && git commit -m "update" && git push`.

### What to expect on free CPU

- The **first** photo is slow: the model weights (~350 MB) download on first
  use, then each photo takes roughly 20–60 s.
- Weights live on non-persistent disk, so they download again after a restart.
- Video is capped at 3 seconds (`MAX_VIDEO_SECONDS`), because per-frame
  enhancement on CPU is about 30 s *per frame*. Treat video as a local-only
  feature.
- Tune anything via Space → Settings → *Variables*: `UPSCALE`,
  `MAX_VIDEO_SECONDS`, `RATE_LIMIT_PHOTO`, `MAX_IMAGE_BYTES`.

### Free GPU note

Hugging Face ZeroGPU is free but Gradio-only, which means the `/api` routes
would not get the GPU — only the `/gradio` handler would. It also comes with a
daily quota (5 minutes of GPU time for free accounts) and needs torch ≥ 2.8.
Worth it only if you rewrite the Space to be Gradio-first.

---

## Option 2 — Google Cloud Run (free tier, card required)

Runs the full app, video included, and scales to zero so an idle deployment
costs nothing.

```bash
gcloud run deploy reviva \
  --source . \
  --dockerfile Dockerfile.cpu \
  --memory 4Gi --cpu 2 \
  --timeout 900 \
  --allow-unauthenticated
```

`Dockerfile.cpu` already honours the `$PORT` that Cloud Run injects. Raise
`--timeout` if you enhance anything large; cold starts are 60–90 s because the
image is big.

---

## Option 3 — Oracle Cloud Always Free (card required, always on)

The Always Free ARM VM (4 vCPU / 24 GB RAM) is the most generous free box that
can host this permanently:

```bash
sudo apt install -y docker.io
git clone https://github.com/CodeWithYeasin/Reviva.git && cd Reviva
sudo docker build -f Dockerfile.cpu -t reviva:cpu .
sudo docker run -d --restart unless-stopped -p 80:8000 reviva:cpu
```

Put Caddy or Nginx in front for HTTPS.

---

## Option 4 — Local / GPU

```bash
./run.sh                              # builds the UI, serves everything on :8000
docker build -t reviva . && docker run --gpus all -p 8000:8000 reviva
```

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `REVIVA_USE_GPU` | `auto` | `1` force GPU, `0` force CPU |
| `UPSCALE` | `2` | 2 or 4 |
| `MAX_IMAGE_BYTES` | 15 MB | upload cap |
| `MAX_VIDEO_SECONDS` | `15` | clip length cap |
| `RATE_LIMIT_PHOTO` | `20/minute` | per client IP |
| `ALLOWED_ORIGINS` | `*` | lock to your domain in production |
| `REVIVA_WORK_DIR` | `/dev/shm/reviva` | per-request scratch space |
| `REVIVA_WEIGHTS_DIR` | `./weights` | where model weights are cached |
| `REVIVA_FRONTEND_DIR` | `frontend/dist` | built UI to serve |

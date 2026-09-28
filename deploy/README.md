# `deploy/` - put genome-mcp online (free)

Three ways to run the web app. All use the `Dockerfile` in the repo root, which listens on `$PORT`
(default 8000) and exposes `/health` for health checks.

## Option 1 - Render (recommended, easiest)

1. Push this repo to GitHub.
2. Create a free account at [render.com](https://render.com) and connect your GitHub.
3. **New + → Blueprint →** choose this repo → **Apply**. Render reads `render.yaml` and builds the Docker image.
4. After 3–5 minutes you get a URL like `https://genome-mcp.onrender.com`. Put it in your README and resume.

**Privacy note for the public demo:** uploaded VCFs are kept in a temp folder for 30 minutes, then deleted.
Add a line on the page or README telling visitors to upload **only synthetic or public data** (e.g. the demo file or 1000 Genomes samples).

> Free Render services sleep after ~15 minutes without traffic; the first visit after that takes ~30–60 seconds to wake up.
> Mention "may take a minute to wake up" next to the link on your resume.

## Option 2 - Hugging Face Spaces (always-on free CPU, popular with AI recruiters)

1. Create an account at [huggingface.co](https://huggingface.co) → **New Space** → name `genome-mcp`, SDK **Docker**, template **Blank**, hardware **CPU basic (free)**.
2. Create an access token (Settings → Access Tokens, role *write*).
3. From your local clone of this repo:

```bash
git remote add space https://huggingface.co/spaces/<hf-username>/genome-mcp
git checkout -b hf-space
cp deploy/huggingface/README.md README.md      # Spaces need a config header in README.md
git commit -am "Hugging Face Space config"
git push space hf-space:main                    # username = HF username, password = the token
git checkout main
```

4. The Space builds and runs at `https://huggingface.co/spaces/<hf-username>/genome-mcp`.

## Option 3 - Docker on your own machine

```bash
docker build -t genome-mcp .
docker run --rm -p 8000:8000 genome-mcp
# open http://localhost:8000
```

## Files

| File | Purpose |
| --- | --- |
| `../Dockerfile` | Container image used by every option |
| `../render.yaml` | Render Blueprint (service type, free plan, health check) |
| `huggingface/README.md` | README with the Space config header (`sdk: docker`, `app_port: 8000`) |

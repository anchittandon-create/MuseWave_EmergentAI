# RunPod Step-by-Step Setup (MusicGen Worker)

This guide deploys a real GPU MusicGen endpoint and connects it to MuseWave.

## 1. Prerequisites

- Docker installed locally.
- RunPod account with billing enabled.
- RunPod API key.
- Logged in to Docker Hub (or GHCR) to push image.

## 2. Build and push worker image

From repo root:

```bash
cd runpod/musicgen-worker
docker build -t <docker-user>/musewave-musicgen:latest .
docker push <docker-user>/musewave-musicgen:latest
```

Replace `<docker-user>` with your Docker Hub username.

## 3. Create RunPod serverless endpoint

1. Open RunPod Console.
2. Go to `Serverless` -> `Create Endpoint`.
3. Endpoint name: `musewave-musicgen`.
4. Container image: `<docker-user>/musewave-musicgen:latest`.
5. GPU: start with `NVIDIA L4` or `A10`.
6. Set environment variables in RunPod endpoint:

```text
MUSICGEN_MODEL=facebook/musicgen-small
MAX_DURATION_SECONDS=45
OUTPUT_FORMAT=wav
```

7. Save and deploy.

## 4. Test endpoint in RunPod

Use RunPod test payload:

```json
{
  "input": {
    "title": "Neon Drift",
    "prompt": "dark electronic pop with punchy drums and airy vocal hook",
    "genres": ["Electronic", "Pop"],
    "duration_seconds": 20,
    "artist_inspiration": "The Weeknd, Kavinsky",
    "vocal_languages": ["English"],
    "lyrics": "night drive energy"
  }
}
```

Expected output contains:

```json
{
  "audio_url": "data:audio/wav;base64,...",
  "duration_seconds": 20,
  "entropy_seed": "...",
  "provider": "runpod_musicgen_worker"
}
```

## 5. Copy endpoint URL

For synchronous calls, URL format is:

```text
https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync
```

`<ENDPOINT_ID>` is shown on your endpoint page.

## 6. Set MuseWave backend env via Vercel CLI

From repo root:

```bash
MUSICGEN_URL='https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync'
RUNPOD_TOKEN='<RUNPOD_API_KEY>'

for env in production preview development; do
  vercel env rm MUSICGEN_API_URL $env --yes --cwd backend || true
  printf '%s' "$MUSICGEN_URL" | vercel env add MUSICGEN_API_URL $env --cwd backend

  vercel env rm MUSICGEN_API_KEY $env --yes --cwd backend || true
  printf '%s' "$RUNPOD_TOKEN" | vercel env add MUSICGEN_API_KEY $env --cwd backend
done

vercel deploy --prod --yes -A vercel.json --cwd backend
```

## 7. Verify from backend

```bash
curl -sS https://muse-wave-backend.vercel.app/api/health | jq
```

Then create a track from UI or call:

```bash
curl -sS -X POST https://muse-wave-backend.vercel.app/api/songs/create \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"",
    "music_prompt":"dark electronic pop with punchy drums",
    "genres":["Electronic","Pop"],
    "duration_seconds":20,
    "vocal_languages":["English"],
    "lyrics":"",
    "artist_inspiration":"The Weeknd",
    "generate_video":false,
    "video_style":"",
    "mode":"single",
    "user_id":"9873945238"
  }' | jq
```

If this returns `audio_url`, endpoint integration is complete.

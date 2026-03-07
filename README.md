# MuseWave (Next.js + Firebase + Gemini Music)

Anonymous AI music generation platform with:
- Gemini music synthesis in fixed 30-second segments
- Deterministic orchestration loop until requested duration is reached
- Progressive stitching into one master file (`/audio/{trackId}_master.wav` + `.mp3`)
- Firestore `tracks` progress updates after each segment
- AI Suggest endpoint powered by Gemini reasoning model
- Home / Create Music / Dashboard UI

## Stack
- Next.js App Router
- Firebase Admin SDK (Firestore + Storage)
- Google Vertex AI (Gemini reasoning + Gemini music model)
- ffmpeg audio pipeline (normalize, stitch, crossfade, mastering)

## Run
```bash
npm install
npm run dev
```

## Required env
Copy `.env.example` to `.env.local` and fill values:
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_PRIVATE_KEY`
- `GEMINI_MUSIC_MODEL`

## API
- `POST /api/suggest`
- `POST /api/tracks`
- `GET /api/tracks`
- `GET /api/tracks/:id`

## Orchestration Flow
1. Create Firestore track doc with `queued/generating` status
2. Create initial master audio artifact in Storage
3. Loop Gemini segment generation (`30s` each)
4. Save each segment to `/tempSegments/{trackId}/segment_n.wav`
5. Stitch segment into master WAV with zero-crossing alignment + 100ms crossfade
6. Overwrite master WAV/MP3 after each segment
7. Update Firestore progress (`durationGenerated`, `segmentsGenerated`, `%`)
8. Final trim + mastering chain + completed status

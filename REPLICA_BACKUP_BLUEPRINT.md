# MuseWave Replica Backup Blueprint

## 1. System Goal
MuseWave is an AI music creation web app that supports:
- AI-assisted input suggestions (music-focused, non-story output)
- Single track generation
- Album generation with per-track custom inputs
- Lyrics synthesis
- Optional AI video generation per track or full album
- Dashboard management with newest-first sorting
- Track and album download

This document is a full backup blueprint for recreating the app behavior and architecture.

## 2. Tech Stack
- Frontend: React (CRA + CRACO), Tailwind-based UI, Axios
- Backend: FastAPI + Motor (MongoDB)
- Database: MongoDB
- AI Suggestions + Lyrics: OpenAI API
- Video Generation: Replicate API (optional)
- Music Generation: Custom provider endpoint via `MUSICGEN_API_URL` (optional)
- Fallback audio: Curated royalty-free library when no provider is configured

## 3. Project Structure
- `frontend/src/App.js`: app shell, auth/session, routes, sidebar layout
- `frontend/src/components/Sidebar.jsx`: left menu + collapse/expand control
- `frontend/src/pages/AuthPage.jsx`: signup/login
- `frontend/src/pages/HomePage.jsx`: landing + feature sections
- `frontend/src/pages/CreateMusicPage.jsx`: single + album creation UX
- `frontend/src/pages/DashboardPage.jsx`: library management, playback, downloads, video actions
- `backend/server.py`: complete API and business logic
- `backend/server_new.py`: compatibility wrapper entrypoint to `server.py`
- `.env.example`: env key contract
- `vercel.json`: frontend-only deployment config (independent)

## 4. Environment Contract
Use `.env` values:

- Required:
1. `MONGO_URL`
2. `DB_NAME`
3. `OPENAI_API_KEY`
4. `REACT_APP_BACKEND_URL` (frontend)

- Optional (for full generation quality):
1. `MUSICGEN_API_URL`
2. `MUSICGEN_API_KEY`
3. `REPLICATE_API_TOKEN`
4. `OPENAI_MODEL` (default: `gpt-4o-mini`)

## 5. Data Models
### 5.1 User
- `id`
- `name`
- `mobile`
- `created_at`

### 5.2 Song
- `id`
- `title`
- `music_prompt`
- `genres[]`
- `duration_seconds`
- `vocal_languages[]`
- `lyrics`
- `artist_inspiration`
- `generate_video`
- `video_style`
- `audio_url`
- `video_url`
- `video_status`
- `video_thumbnail`
- `cover_art_url`
- `accuracy_percentage` (single flow)
- `album_id` (nullable)
- `track_number` (album tracks)
- `user_id`
- `created_at`
- `is_demo` (true when fallback library is used)
- `generation_provider`

### 5.3 Album
- `id`
- `title`
- `music_prompt`
- `genres[]`
- `vocal_languages[]`
- `lyrics`
- `artist_inspiration`
- `generate_video`
- `video_style`
- `cover_art_url`
- `num_songs`
- `user_id`
- `created_at`

### 5.4 Album Per-Track Input (request-only)
- `title`
- `music_prompt` (required per track)
- `genres[]`
- `duration_seconds`
- `vocal_languages[]`
- `lyrics`
- `artist_inspiration`
- `video_style`

## 6. API Surface
Prefix: `/api`

### Auth
- `POST /auth/signup`
- `POST /auth/login`

### Knowledge Base
- `GET /genres`
- `GET /languages`
- `GET /artists`
- `GET /video-styles`

### AI Assist
- `POST /suggest`
  - Input: `field`, `current_value`, `context`
  - Output: `suggestion`, `field`

### Creation
- `POST /songs/create`
- `POST /albums/create`
  - Supports `album_songs[]` so each track can have full custom inputs

### Retrieval
- `GET /songs/user/{user_id}`
- `GET /albums/user/{user_id}`
- `GET /dashboard/{user_id}`

### Download
- `GET /songs/{song_id}/download?user_id=...`
- `GET /albums/{album_id}/download?user_id=...`

### Video
- `POST /songs/{song_id}/generate-video?user_id=...`
- `GET /songs/{song_id}/video-status?user_id=...`
- `POST /albums/{album_id}/generate-videos?user_id=...`

### Health
- `GET /health`
- `GET /api/health`

## 7. Core Logic Flows
### 7.1 AI Suggestion Flow
1. Frontend sends `field + context` to `/suggest`.
2. Backend builds a high-diversity prompt with uniqueness seed.
3. OpenAI generates candidate text.
4. Backend validates music-specific output:
- Filters story/poetry-like phrasing
- Validates list fields (`genres`, `vocal_languages`)
- Deduplicates recent suggestions by field (in-memory)
5. Frontend applies suggestion to relevant field (single or selected album track).

### 7.2 Single Track Flow
1. User completes single-form inputs.
2. Backend generates title if empty.
3. Backend generates lyrics if vocal languages are set and lyrics are empty.
4. Backend tries real audio generation via `MUSICGEN_API_URL`.
5. If provider is unavailable/fails, backend falls back to curated audio library (`is_demo=true`).
6. Song is saved and returned to frontend.

### 7.3 Album Flow (Per-Track Required)
1. User selects album mode and track count.
2. UI asks full inputs per track (title, prompt, duration, genres, languages, lyrics, artist inspiration, video style).
3. Frontend sends `album_songs[]` payload.
4. Backend validates each track has `music_prompt`.
5. For each track:
- Generate/fill title
- Generate lyrics when missing and vocals are present
- Generate audio via provider or fallback
- Save song with `track_number`
6. Album + all songs are returned.

### 7.4 Video Generation Flow
1. User triggers per-song or full-album video generation.
2. If `REPLICATE_API_TOKEN` exists:
- Marks status `processing`
- Runs background task
- Updates DB when completed
3. Without token:
- Uses sample fallback video URL
- Marks as completed

### 7.5 Download Flow
- Album download creates ZIP in-memory:
1. Fetch album + songs
2. Pull audio binary for each track URL
3. Add tracks + `album_info.json`
4. Stream ZIP response

## 8. Frontend UX Logic
### 8.1 Sidebar / LHS Menu
- Clear hamburger icon button placed to the left of brand
- Collapse/expand behavior adjusts content margin (`ml-20` vs `ml-64`)
- Brand: `MuseWave`

### 8.2 Create Page
- Modes: Single / Album
- Album mode has per-track collapsible sections (Track 1, Track 2, ...)
- Each track section includes all key creative inputs
- AI suggest available at field-level
- Result panel supports:
- Audio playback
- Download
- Album download
- Album video generation trigger

### 8.3 Dashboard
- Songs sorted descending by `created_at`
- Albums sorted descending by `created_at`
- Album tracks sorted descending by `created_at`
- Expanded album displays song details per row before next song
- Includes playback, video actions, and download actions

## 9. Sorting Rules (Enforced)
- Backend and frontend both apply descending date order for robustness.
- Scope:
1. Single songs list
2. Albums list
3. Songs inside each album

## 10. Deployment Blueprint (Independent)
### Frontend (Vercel)
1. Deploy `frontend` build via root `vercel.json`.
2. Set env var in Vercel project:
- `REACT_APP_BACKEND_URL=https://<your-backend-domain>`
3. Build command already configured.

### Backend (FastAPI)
Deploy separately (Railway/Render/Fly/VM/K8s):
1. `pip install -r backend/requirements.txt`
2. Set env vars from `.env.example`
3. Run: `uvicorn backend.server:app --host 0.0.0.0 --port 8000`

### MongoDB
- Use Atlas or managed Mongo
- Ensure network access + credentials

## 11. Required Keys From You
To avoid current AI errors and template fallback behavior, you should provide:
1. `OPENAI_API_KEY` (required for suggestions + lyrics synthesis)
2. `MUSICGEN_API_URL` + `MUSICGEN_API_KEY` (recommended for real track generation)
3. `REPLICATE_API_TOKEN` (optional for real video generation)

Without these, the system still works but uses fallback behavior for missing providers.

## 12. Backup / Rebuild Checklist
1. Restore codebase files listed in Section 3.
2. Restore `.env` values.
3. Restore MongoDB collections: `users`, `songs`, `albums`.
4. Deploy backend.
5. Deploy frontend with `REACT_APP_BACKEND_URL` set.
6. Validate health and creation endpoints.
7. Validate dashboard sorting and media actions.

## 13. Verification Commands
- Backend health:
`curl http://localhost:8000/api/health`

- Suggestion test:
`curl -X POST http://localhost:8000/api/suggest -H "Content-Type: application/json" -d '{"field":"music_prompt","current_value":"","context":{"genres":["Electronic"],"music_prompt":"dark cinematic bass"}}'`

- Single create test:
`curl -X POST http://localhost:8000/api/songs/create -H "Content-Type: application/json" -d '{"title":"","music_prompt":"deep atmospheric electronic with cinematic drums","genres":["Electronic"],"duration_seconds":30,"vocal_languages":["English"],"lyrics":"","artist_inspiration":"","generate_video":false,"video_style":"","user_id":"<user-id>"}'`

- Album create with per-track payload test:
`curl -X POST http://localhost:8000/api/albums/create -H "Content-Type: application/json" -d '{"title":"Global Echoes","music_prompt":"","genres":[],"vocal_languages":[],"lyrics":"","artist_inspiration":"","generate_video":true,"video_style":"","num_songs":2,"user_id":"<user-id>","album_songs":[{"title":"","music_prompt":"afro-electronic groove with live percussion","genres":["Afrobeats","Electronic"],"duration_seconds":35,"vocal_languages":["English"],"lyrics":"","artist_inspiration":"","video_style":"street documentary"},{"title":"","music_prompt":"ambient post-rock build with choir textures","genres":["Ambient","Post-Rock"],"duration_seconds":42,"vocal_languages":["Instrumental"],"lyrics":"","artist_inspiration":"","video_style":"cinematic nature"}]}'`

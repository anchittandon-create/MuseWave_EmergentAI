# MuseWave

Independent AI music creation app with:
- AI field suggestions
- Single + album generation
- Per-track album input forms
- Lyrics synthesis
- Optional AI video generation
- Track/album download

## Full Replica Backup Documentation
See: `REPLICA_BACKUP_BLUEPRINT.md`

## Quick Start

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Set `REACT_APP_BACKEND_URL` to your backend base URL.
Use the host root (example: `https://your-backend-host.com`), not `/api`, `/dashboard`, or GitHub URLs.
For deployment, configure this env var in Vercel project settings.

#!/usr/bin/env bash

# MuseWave Deployment Architecture Diagram
# This shows how the frontend and backend are connected in production

cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                   MuseWave Deployment Architecture                        ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                          USER'S BROWSER                                  │
│  https://your-app.vercel.app                                             │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         │ GET /
                         │ GET /create
                         │ GET /dashboard
                         │
                         ▼
        ┌─────────────────────────────────┐
        │       VERCEL (Frontend)         │
        │  Creates React App Deployment   │
        │                                 │
        │  ✓ Serves index.html            │
        │  ✓ Serves static files          │
        │  ✓ Runs vercel.json rewrites    │
        └────────────┬────────────────────┘
                     │
                     │ vercel.json routing:
                     │
         ┌───────────┴──────────────┐
         │                          │
         ▼ /api/*                   ▼ /* (all other)
    ┌─────────────┐           ┌──────────────┐
    │ Proxy to    │           │ Serve        │
    │ Backend API │           │ index.html   │
    │             │           │              │
    │ ↓↓↓         │           │ React Router │
    │             │           │ takes over   │
    └────┬────────┘           └──────────────┘
         │
         │ HTTPS Request
         │ POST /api/songs
         │ POST /api/auth/login
         │ GET /api/genres
         │
         ▼
    ┌──────────────────────────────┐
    │  Backend Server (Railway)    │
    │  https://your-backend.app    │
    │                              │
    │  FastAPI Application         │
    │  - User Authentication       │
    │  - Song Creation             │
    │  - Database Operations       │
    │  - AI Integration            │
    └────────────┬─────────────────┘
                 │
                 │ MongoDB Query
                 │
                 ▼
        ┌──────────────────────┐
        │  MongoDB Atlas       │
        │  (Cloud Database)    │
        │                      │
        │  Collections:        │
        │  - users             │
        │  - songs             │
        │  - albums            │
        └──────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════╗
║                           DEPLOYMENT FLOW                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝

1. USER VISITS APP
   ├─ Browser requests: https://your-app.vercel.app
   ├─ Vercel receives request
   └─ Checks vercel.json rewrites

2. VERCEL REWRITES
   ├─ Request path starts with /api/?
   │  └─ Proxy to backend: https://your-backend.app/api/...
   │
   └─ All other paths?
      └─ Serve index.html (React app)

3. REACT APP LOADS
   ├─ Runs in browser
   ├─ React Router handles navigation
   │  ├─ / → HomePage
   │  ├─ /create → CreateMusicPage
   │  └─ /dashboard → DashboardPage
   │
   └─ When user interacts:
      └─ Makes API calls to /api/*

4. API CALLS
   ├─ Request: POST /api/songs
   ├─ Vercel rewrite: https://your-backend.app/api/songs
   ├─ Backend FastAPI processes
   ├─ Queries MongoDB
   └─ Returns response to frontend

5. FRONTEND UPDATES
   ├─ React receives API response
   ├─ Updates state
   ├─ Re-renders UI
   └─ User sees results


╔═══════════════════════════════════════════════════════════════════════════╗
║                     ENVIRONMENT VARIABLES FLOW                            ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─ Frontend (Vercel)
│  ├─ REACT_APP_BACKEND_URL
│  │  └─ Used in App.js: const API = `${BACKEND_URL}/api`
│  │     Example: https://your-backend.app/api
│  │
│  └─ Vercel API routes
│     └─ Rewrites /api/* to REACT_APP_BACKEND_URL


┌─ Backend (Railway/Render)
│  ├─ MONGO_URL → MongoDB Atlas connection
│  │  └─ mongodb+srv://user:pass@cluster.mongodb.net
│  │
│  ├─ DB_NAME → Database name
│  │  └─ muzify_db
│  │
│  ├─ EMERGENT_LLM_KEY → AI service API key
│  │  └─ Used for song suggestions
│  │
│  ├─ CORS_ORIGINS → Allowed frontend URLs
│  │  └─ https://your-app.vercel.app
│  │     Prevents CORS errors
│  │
│  └─ PORT → Server port
│     └─ 8000 (default)


╔═══════════════════════════════════════════════════════════════════════════╗
║                         REQUEST EXAMPLE                                   ║
╚═══════════════════════════════════════════════════════════════════════════╝

USER CREATES A SONG:

1. Clicks "Create Song" button
   └─ Frontend Form Component

2. User fills form:
   ├─ Title: "Summer Vibes"
   ├─ Genre: ["Electronic", "Pop"]
   ├─ Prompt: "Uplifting summer song"
   └─ Duration: 30 seconds

3. User clicks "Generate"
   └─ React calls API:
      POST /api/songs
      {
        "title": "Summer Vibes",
        "genres": ["Electronic", "Pop"],
        "music_prompt": "Uplifting summer song",
        "duration_seconds": 30,
        "user_id": "user123"
      }

4. Vercel Routes Request
   └─ URL: /api/songs
      vercel.json sees /api/*
      Rewrites to: https://your-backend.app/api/songs

5. Backend Receives Request
   ├─ FastAPI handler processes
   ├─ Generates unique song ID
   ├─ Selects audio from library
   ├─ Saves to MongoDB
   └─ Returns response:
      {
        "id": "song_123",
        "title": "Summer Vibes",
        "audio_url": "https://...",
        "status": "ready"
      }

6. Frontend Receives Response
   ├─ React updates state
   ├─ Shows success message
   ├─ Updates song list
   └─ User sees new song


╔═══════════════════════════════════════════════════════════════════════════╗
║                      TROUBLESHOOTING DIAGRAM                              ║
╚═══════════════════════════════════════════════════════════════════════════╝

❌ 404 NOT_FOUND on https://your-app.vercel.app
   ├─ Problem: Frontend not being served
   │  ├─ vercel.json missing or wrong
   │  ├─ Build didn't complete
   │  └─ Wrong build output directory
   │
   └─ Solution:
      ├─ Check vercel.json exists in root
      ├─ Check Vercel build logs
      └─ Rebuild frontend

❌ CORS Error on API calls
   ├─ Problem: Backend rejecting requests from frontend
   │  ├─ CORS_ORIGINS not set correctly
   │  ├─ Frontend URL doesn't match
   │  └─ Backend not restarted after env change
   │
   └─ Solution:
      ├─ Update CORS_ORIGINS environment variable
      ├─ Use exact frontend URL
      └─ Restart backend service

❌ API returns 404
   ├─ Problem: Wrong backend URL in frontend
   │  ├─ REACT_APP_BACKEND_URL is wrong
   │  ├─ Backend not deployed
   │  └─ Backend service down
   │
   └─ Solution:
      ├─ Check REACT_APP_BACKEND_URL in .env.production
      ├─ Test backend directly: curl https://your-backend.app/api/health
      └─ Check backend platform dashboard

❌ Database errors
   ├─ Problem: Backend can't connect to MongoDB
   │  ├─ MONGO_URL wrong
   │  ├─ Database doesn't exist
   │  └─ IP not whitelisted in MongoDB Atlas
   │
   └─ Solution:
      ├─ Verify MONGO_URL environment variable
      ├─ Check MongoDB Atlas network access
      └─ Create database if needed


EOF

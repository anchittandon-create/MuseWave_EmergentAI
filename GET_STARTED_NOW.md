# 🚀 SoundForge - Getting Started in 5 Minutes

## CRITICAL FIRST STEPS

### Step 1: Get OpenAI API Key (5 min)
```
1. Go to https://platform.openai.com/api/keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy key (starts with sk-proj-...)
5. SAVE IT SAFELY
```

### Step 2: Get MongoDB URL (5 min)
**Option A - Local (Easy for testing):**
```
- Install MongoDB: https://docs.mongodb.com/manual/installation/
- URL: mongodb://localhost:27017
```

**Option B - Cloud (Recommended):**
```
1. Go to https://www.mongodb.com/cloud/atlas
2. Sign up, create cluster
3. Click "Connect" > "Drivers" > "Python"
4. Copy connection string
```

### Step 3: Create .env File
```bash
cd /Users/Anchit.Tandon/Desktop/MuseWave_EmergentAI
cp .env.example .env
# Edit .env and add your keys
```

### Step 4: Start Backend
```bash
cd backend
pip install -r requirements.txt
python server_new.py
# Should say: "✓ MongoDB connected" + "🚀 Starting SoundForge API"
```

### Step 5: Start Frontend
```bash
# New terminal
cd frontend
npm install
npm start
# Opens http://localhost:3000
```

### Step 6: Test
1. Open http://localhost:3000
2. Signup
3. Create music - Click 💡 next to Title
4. See AI-generated title appear
5. Done! ✅

---

## Files Created

| File | What It Does |
|------|-------------|
| `backend/server_new.py` | New backend (replaces old server.py) |
| `COMPLETE_SYSTEM_DOCUMENTATION.md` | Full technical design |
| `SOUNDFORGE_IMPLEMENTATION_GUIDE.md` | Detailed implementation guide |
| `.env.example` | Environment template |

## Files Updated

| File | Change |
|------|--------|
| `backend/requirements.txt` | Removed emergent (126→15 packages) |

## Files To Update Next

| File | What To Do |
|------|-----------|
| `frontend/src/App.js` | Change API to `http://localhost:8000/api` |
| `frontend/src/components/Sidebar.jsx` | Hamburger menu + "SoundForge" brand |
| `frontend/src/pages/CreateMusicPage.jsx` | Sequential album forms |

---

## Quick Verification

```bash
# Test 1: Backend health
curl http://localhost:8000/api/health

# Test 2: Get genres
curl http://localhost:8000/api/genres

# Test 3: AI suggestion
curl -X POST http://localhost:8000/api/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "field": "title",
    "context": {"music_prompt": "Electronic music"}
  }'
```

---

## Key Improvements

✅ No more Emergent dependency  
✅ Real OpenAI GPT-4 integration  
✅ Music-specific AI suggestions  
✅ 140+ genres, 50+ languages  
✅ 3-layer validation (no poetry)  
✅ 15 minimal dependencies (was 126)  
✅ Clear, simple, maintainable code  

---

## Need Help?

1. Check `SOUNDFORGE_IMPLEMENTATION_GUIDE.md` for detailed setup
2. Check `COMPLETE_SYSTEM_DOCUMENTATION.md` for architecture
3. Check `.env.example` for environment variable instructions
4. Check backend logs (first thing when errors occur)
5. Test health: `curl http://localhost:8000/api/health`

---

## What's Next?

1. ✅ Get API keys & setup .env
2. ✅ Run backend & frontend
3. ✅ Test basic music creation
4. ⏳ Update Sidebar with hamburger menu
5. ⏳ Fix album UI sequential forms
6. ⏳ Deploy to Vercel

All you need to know is in the 3 guide files. Start with SOUNDFORGE_IMPLEMENTATION_GUIDE.md!

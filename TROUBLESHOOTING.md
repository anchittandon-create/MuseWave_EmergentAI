# Troubleshooting: 404 NOT_FOUND Error

## What Caused the Error

You were getting a **404 NOT_FOUND** error because:

1. **Frontend wasn't served** - Your backend only exposed API routes (`/api/*`), not the React app
2. **Missing routing configuration** - No `vercel.json` to tell Vercel how to handle routes
3. **Disconnected services** - Frontend and backend weren't properly connected

## Root Cause Explanation

When you visited `https://your-domain.com`:
```
❌ WRONG (What was happening):
  Request → Vercel
           → Looks for /index.html
           → Can't find static files
           → Returns 404 error

✅ CORRECT (What should happen):
  Request → Vercel
           → Serves frontend/build/index.html
           → React Router takes over
           → SPA loads and makes API calls to backend
           → /api/* calls proxy to backend server
```

## How It's Fixed Now

### 1. Backend Now Serves Frontend
```python
# In backend/server.py:
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # Serves index.html for all non-API routes
    # Allows React Router to handle routing
```

### 2. Vercel Configured with Rewrites
```json
// vercel.json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-url/api/:path*"
    },
    {
      "source": "/((?!api).*)",
      "destination": "/index.html"
    }
  ]
}
```

### 3. Environment Variables Separated
- **Frontend**: Knows backend URL via `REACT_APP_BACKEND_URL`
- **Backend**: Knows frontend URL via `CORS_ORIGINS`

## Common Issues & Solutions

### Issue 1: Still Getting 404
**Possible causes:**
- Frontend not built (`npm run build`)
- `vercel.json` not deployed
- Build output directory wrong

**Solutions:**
1. Verify frontend was built: Check `frontend/build/index.html` exists
2. Verify `vercel.json` is in root directory
3. In Vercel dashboard, check "Build Logs" for errors
4. Redeploy on Vercel

### Issue 2: API Calls Failing (Network Error)
**Possible causes:**
- `REACT_APP_BACKEND_URL` not set correctly
- Backend not deployed
- CORS_ORIGINS not configured on backend

**Solutions:**
1. Check `frontend/.env.production` has correct URL
2. Verify backend is running: `curl https://your-backend-url/api/health`
3. Update backend's `CORS_ORIGINS` environment variable
4. Restart backend after CORS update

### Issue 3: Backend Not Responding
**Possible causes:**
- Backend service is down
- Wrong URL
- Database connection failed

**Solutions:**
1. Check backend platform dashboard (Railway, Render, etc.)
2. View application logs
3. Verify `MONGO_URL` environment variable is set
4. Check MongoDB Atlas network access settings

### Issue 4: Frontend Works, But API Calls Don't
**Possible causes:**
- CORS not configured
- API endpoint paths wrong
- Backend not deployed to correct URL

**Solutions:**
```bash
# Test backend directly
curl -H "Origin: https://your-frontend-url" \
     https://your-backend-url/api/health

# Should see:
# {"status": "healthy", "version": "2.1"}
```

If CORS error:
1. Update backend's CORS_ORIGINS:
   ```
   CORS_ORIGINS=https://your-frontend-url.vercel.app
   ```
2. Restart backend
3. Redeploy frontend

## Verification Checklist

✅ **Frontend Deployment**
- [ ] Vercel project created and building
- [ ] `vercel.json` in root with rewrites
- [ ] `frontend/.env.production` has `REACT_APP_BACKEND_URL`
- [ ] Build logs show no errors
- [ ] Homepage loads without 404

✅ **Backend Deployment**
- [ ] Backend service running (Railway/Render/etc)
- [ ] All environment variables set
- [ ] MongoDB connection working
- [ ] `CORS_ORIGINS` includes frontend URL
- [ ] `/api/health` returns 200 status

✅ **Integration**
- [ ] Frontend loads
- [ ] Login page appears
- [ ] Network tab shows API calls to backend
- [ ] Can create a song
- [ ] Data appears in MongoDB

## Deployment Flow Diagram

```
GitHub Repository
    ↓
┌─────────────────────────────────────┐
│         GitHub Actions CI/CD         │
└──────┬──────────────────────┬────────┘
       │                      │
       ↓                      ↓
  Vercel Backend         Railway Backend
  (Frontend Build)       (FastAPI Server)
       │                      │
       └──────────────────────┘
              ↓
         User Visits URL
              ↓
         index.html served
              ↓
         React App Loads
              ↓
         /api/* calls routed
              ↓
         Backend API Response
```

## Testing After Deployment

### Test 1: Frontend Loads
```bash
curl https://your-frontend-url
# Should return HTML with React app code
```

### Test 2: API Works
```bash
curl https://your-backend-url/api/health
# Should return: {"status": "healthy", ...}
```

### Test 3: CORS Working
Open browser DevTools and try API call in console:
```javascript
fetch('https://your-backend-url/api/genres')
  .then(r => r.json())
  .then(d => console.log(d))
  // Should show genres list, not CORS error
```

### Test 4: Full Integration
1. Visit https://your-frontend-url
2. Open DevTools → Network tab
3. Try logging in
4. Check that API call shows:
   - Request to `https://your-backend-url/api/...`
   - Status: 200-201
   - Response shows data

## Still Having Issues?

1. Check `DEPLOYMENT.md` for step-by-step guide
2. View platform logs:
   - Vercel: Project Settings → Deployments → Build Logs
   - Railway: Logs tab
   - Check MongoDB Atlas for connection errors
3. Use error ID to search for help:
   - Your error ID: `bom1:bom1::npb7g-1771147935344-a5bc9f3a4b95`
   - This is Vercel trying to serve frontend but config was missing
4. Verify all environment variables are exactly correct
5. Try redeploying both frontend and backend

## Quick Reference Commands

```bash
# Build frontend locally
cd frontend && npm run build

# Test backend locally
cd backend
export MONGO_URL=your_mongodb_url
export EMERGENT_LLM_KEY=your_key
pip install -r requirements.txt
uvicorn server:app --reload

# Test frontend locally
cd frontend && npm start
```

Good luck! 🚀

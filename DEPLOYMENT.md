# MuseWave Deployment Guide

## 🚀 Deployment Architecture

MuseWave is a full-stack application with:
- **Frontend**: React app (deployed on Vercel)
- **Backend**: FastAPI server (deployed separately)

## 📋 Prerequisites

1. **Vercel Account** - for frontend deployment
2. **Backend Hosting** - Choose one:
   - Railway.app (recommended)
   - Render.com
   - Heroku
   - AWS
   - DigitalOcean

3. **MongoDB Database** - MongoDB Atlas (cloud) or self-hosted

## 🔧 Backend Deployment (FastAPI)

### Option 1: Railway.app (Recommended)

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/MuseWave_EmergentAI.git
   git push -u origin main
   ```

2. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository
   - Configure environment variables:
     ```
     MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net
     DB_NAME=muzify_db
     EMERGENT_LLM_KEY=your_api_key
     CORS_ORIGINS=https://your-frontend-url.vercel.app
     PORT=8000
     ```

3. **Get your backend URL** from Railway dashboard
   - It will look like: `https://your-app-name.railway.app`

### Option 2: Render.com

1. **Connect repository** on render.com
2. **Create a new Web Service**
3. **Build Command**: `pip install -r backend/requirements.txt`
4. **Start Command**: `cd backend && uvicorn server:app --host 0.0.0.0 --port 8000`
5. **Set Environment Variables** (same as Railway)
6. **Deploy**

## 🎨 Frontend Deployment (Vercel)

### Step 1: Prepare for Production

1. **Update backend URL** in `frontend/.env.production`:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.railway.app
   ```

2. **Build locally to test**:
   ```bash
   cd frontend
   npm run build
   ```

### Step 2: Deploy to Vercel

1. **Push to GitHub** (if not already done)

2. **Go to [vercel.com](https://vercel.com)**
   - Click "New Project"
   - Import your GitHub repository
   - Select "MuseWave_EmergentAI" folder as root

3. **Configure Build Settings**:
   - **Framework**: Create React App
   - **Build Command**: `npm run build` (in frontend directory)
   - **Output Directory**: `frontend/build`
   - **Install Command**: `cd frontend && npm install`

4. **Environment Variables** (in Vercel Project Settings):
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.railway.app
   ```

5. **Deploy** - Vercel will automatically build and deploy

## 🔗 Connecting Frontend to Backend

After deployment:

1. **Update CORS on Backend**:
   - Set `CORS_ORIGINS` environment variable to your frontend URL
   - Example: `https://musewave-123.vercel.app`

2. **Update Frontend Environment**:
   - Update `frontend/.env.production` with your backend URL
   - Redeploy frontend

3. **Test the Connection**:
   - Visit your frontend URL
   - Open browser DevTools → Network tab
   - Try creating a song
   - Verify API calls go to your backend

## 📝 Environment Variables Reference

### Backend (FastAPI)
```
MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net
DB_NAME=muzify_db
EMERGENT_LLM_KEY=your_emergent_api_key
CORS_ORIGINS=https://your-vercel-url.vercel.app
PORT=8000
```

### Frontend
```
REACT_APP_BACKEND_URL=https://your-backend-url.com
```

## 🧪 Testing Deployment

1. **Check Backend Health**:
   ```bash
   curl https://your-backend-url/api/health
   ```
   Expected response:
   ```json
   {"status": "healthy", "version": "2.1", "mode": "demo"}
   ```

2. **Check Frontend**:
   - Visit your Vercel URL
   - Should see the login page
   - Network requests should go to your backend

3. **Test Full Flow**:
   - Login
   - Create a song
   - Check MongoDB to see saved data

## 🐛 Troubleshooting

### 404 Error on Frontend
- ✅ Verify `vercel.json` exists with correct rewrites
- ✅ Check that build completed successfully on Vercel
- ✅ Check that frontend is deployed, not just backend

### Backend 404 Errors
- ✅ Check backend URL in `REACT_APP_BACKEND_URL`
- ✅ Verify CORS_ORIGINS includes your Vercel domain
- ✅ Test API endpoints directly: `curl https://your-backend-url/api/health`

### CORS Errors
- ✅ Update `CORS_ORIGINS` environment variable
- ✅ Make sure frontend URL matches exactly
- ✅ Check browser console for specific error

### MongoDB Connection Issues
- ✅ Verify `MONGO_URL` is correct
- ✅ Check MongoDB Atlas network access (IP whitelist)
- ✅ Ensure database exists

## 📊 Monitoring

1. **Vercel**: Dashboard shows deployment status and analytics
2. **Railway/Render**: View logs from the dashboard
3. **MongoDB Atlas**: View connection metrics and data usage

## 🔄 Redeploying After Changes

### Frontend Changes
```bash
git add .
git commit -m "Update frontend"
git push
# Vercel auto-deploys
```

### Backend Changes
```bash
git add .
git commit -m "Update backend"
git push
# Railway/Render auto-deploys
```

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vercel React Deployment](https://vercel.com/docs/frameworks/create-react-app)
- [Railway Documentation](https://docs.railway.app/)
- [MongoDB Atlas](https://docs.atlas.mongodb.com/)

---

For more help, check the logs on your deployment platform!

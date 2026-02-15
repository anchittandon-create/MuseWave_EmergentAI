#!/bin/bash

# MuseWave Deployment Script
# This script helps you deploy the application step by step

set -e

echo "🎵 MuseWave Deployment Helper"
echo "============================="
echo ""

# Check if frontend build exists
if [ ! -d "frontend/build" ]; then
    echo "📦 Building frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
    echo "✅ Frontend built successfully!"
else
    echo "✅ Frontend build already exists"
fi

echo ""
echo "📋 Deployment Checklist:"
echo "========================"
echo ""
echo "Backend Deployment:"
echo "  1. Choose hosting platform (Railway.app recommended)"
echo "  2. Push code to GitHub"
echo "  3. Connect repository to your platform"
echo "  4. Set environment variables:"
echo "     - MONGO_URL (MongoDB connection string)"
echo "     - DB_NAME (database name)"
echo "     - EMERGENT_LLM_KEY (API key)"
echo "     - CORS_ORIGINS (frontend URL)"
echo "  5. Note your backend URL"
echo ""
echo "Frontend Deployment:"
echo "  1. Update frontend/.env.production with backend URL"
echo "  2. Go to vercel.com and import GitHub repo"
echo "  3. Set environment variable REACT_APP_BACKEND_URL"
echo "  4. Deploy"
echo ""
echo "Testing:"
echo "  1. Visit your Vercel URL"
echo "  2. Check browser DevTools Network tab"
echo "  3. Test API calls to backend"
echo ""
echo "For detailed instructions, see DEPLOYMENT.md"

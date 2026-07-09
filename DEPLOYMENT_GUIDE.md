# Production Deployment Guide

This guide walks through deploying the Video Captioning application to production on Vercel (frontend) and Render (backend).

## Architecture

```
[User's Browser] 
      ↓
[Vercel Frontend] (React + Vite)
      ↓
[Render Backend] (FastAPI)
      ↓
[Gemini 2.5 Flash API]
```

---

## Prerequisites

- GitHub repository with code committed
- Vercel account (https://vercel.com)
- Render account (https://render.com)
- Gemini API key from Google AI Studio (https://aistudio.google.com)

---

## Part 1: Deploy Backend to Render

### Step 1: Prepare Environment Variables

1. Copy `.env.example` to `.env` and fill in:
   ```
   GEMINI_API_KEY=your-actual-key
   GEMINI_MODEL=gemini-2.5-flash
   ENVIRONMENT=production
   ```
   
   **IMPORTANT**: Do NOT commit `.env` to GitHub. It should be in `.gitignore`.

2. Get your Gemini API key:
   - Visit https://aistudio.google.com
   - Create a new API key
   - Copy the key value

### Step 2: Create Render Web Service

1. Go to https://render.com/dashboard
2. Click "New" → "Web Service"
3. Select your GitHub repository
4. Configure:
   - **Name**: `video-captioning-api` (or your choice)
   - **Environment**: Python 3
   - **Build Command**: 
     ```
     pip install -r requirements.txt && pip install -r api/requirements.txt
     ```
   - **Start Command**:
     ```
     cd api && uvicorn main:app --host 0.0.0.0 --port 10000
     ```
   - **Plan**: Free tier is fine for testing

### Step 3: Set Environment Variables on Render

In the Render dashboard, go to your service's "Environment" tab and add:

```
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash
FRAME_COUNT=5
ENVIRONMENT=production
CORS_ORIGINS=https://your-vercel-domain.vercel.app,https://your-custom-domain.com
```

**Note**: Get your Vercel domain AFTER deploying the frontend.

### Step 4: Deploy

Click "Create Web Service". Render will automatically deploy when you push to GitHub.

Once deployed, you'll get a URL like: `https://video-captioning-api.onrender.com`

### Step 5: Test Backend

```bash
curl https://video-captioning-api.onrender.com/api/health
```

Response should show:
```json
{
  "status": "ok",
  "model": "gemini-2.5-flash",
  "environment": "production",
  "api_key_configured": true,
  "cors_origins": [...]
}
```

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Connect Repository

1. Go to https://vercel.com/dashboard
2. Click "Add New..." → "Project"
3. Select your GitHub repository
4. Click "Import"

### Step 2: Configure Build Settings

1. In the "Configure Project" dialog:
   - **Framework Preset**: Vite
   - **Build Command**: `cd web && npm run build`
   - **Output Directory**: `web/dist`
   - **Install Command**: `npm install --prefix web`

2. Click "Deploy"

### Step 3: Get Your Vercel Domain

After deployment, you'll get a URL like:
```
https://your-project.vercel.app
```

### Step 4: Set Frontend Environment Variables

1. Go to your Vercel project Settings
2. Navigate to "Environment Variables"
3. Add:
   ```
   VITE_API_BASE_URL = https://video-captioning-api.onrender.com
   ```
4. Set "Environments" to "Production"
5. Click "Save"

### Step 5: Update Backend CORS

1. Go back to Render dashboard
2. Edit the `CORS_ORIGINS` environment variable to include your Vercel domain:
   ```
   CORS_ORIGINS=https://your-project.vercel.app
   ```
3. Render will auto-redeploy with the new environment variables

### Step 6: Test Frontend

1. Open `https://your-project.vercel.app` in your browser
2. Try uploading a video
3. Check browser console (F12) for logs
4. If there are errors, check:
   - Browser DevTools → Console tab for error messages
   - Render logs for backend errors

---

## Troubleshooting

### Frontend loads but no output / "Cannot connect to backend"

**Problem**: The frontend cannot reach the backend API.

**Solutions**:

1. Check `VITE_API_BASE_URL` is set correctly in Vercel environment
2. Verify backend URL is accessible:
   ```bash
   curl https://video-captioning-api.onrender.com/api/health
   ```
3. Check CORS in Render logs:
   ```bash
   # Render dashboard → Logs tab
   # Look for: "CORS configured for origins"
   ```
4. Verify your Vercel domain is in `CORS_ORIGINS` on Render

### "CORS error" in browser console

**Problem**: Browser is blocking the request due to CORS policy.

**Solution**: Your Vercel domain must be in Render's `CORS_ORIGINS` environment variable.

Example: If your frontend is at `https://myapp.vercel.app`, then `CORS_ORIGINS` must include it:
```
CORS_ORIGINS=https://myapp.vercel.app
```

### Backend returns "401 Unauthorized" or "API key error"

**Problem**: Gemini API key is missing or invalid.

**Solution**:
1. Verify the API key is set in Render environment variables
2. Get a fresh key from https://aistudio.google.com
3. Update Render environment variable and redeploy

### Slow uploads or timeouts

**Problem**: Video processing takes too long or times out.

**Causes & Solutions**:
- Free Render tier may be slow. Upgrade to "Standard" if needed.
- Check `FRAME_COUNT` value (default 5). Lower it for faster processing.
- Ensure video file is under 100MB
- Check Render logs for specific errors

### "Invalid video format" error

**Problem**: Supported formats (MP4, WebM, MOV) are being rejected.

**Solution**:
- Convert video to MP4: `ffmpeg -i input.mov -c:v libx264 output.mp4`
- Check file is actually a valid video file
- Check file size is under 100MB

---

## Environment Variables Reference

### Frontend (Vercel)

| Variable | Example | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `https://video-captioning-api.onrender.com` | Backend API URL |

### Backend (Render)

| Variable | Example | Required | Description |
|----------|---------|----------|-------------|
| `GEMINI_API_KEY` | `AIza...` | ✓ | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` |  | Model name (default shown) |
| `ENVIRONMENT` | `production` |  | Deployment environment |
| `CORS_ORIGINS` | `https://myapp.vercel.app` |  | Comma-separated frontend URLs |
| `FRAME_COUNT` | `5` |  | Frames to extract from video |
| `TEMPERATURE` | `0.2` |  | Gemini temperature (0-1) |

---

## Health Checks

### Verify Backend is Running

```bash
curl https://video-captioning-api.onrender.com/api/health
```

Expected response (200 OK):
```json
{
  "status": "ok",
  "model": "gemini-2.5-flash",
  "environment": "production",
  "api_key_configured": true,
  "cors_origins": ["https://myapp.vercel.app"]
}
```

### Verify Frontend Can Reach Backend

1. Open browser DevTools (F12)
2. Go to Console tab
3. Try uploading a video
4. Look for logs like:
   ```
   [API] POST https://video-captioning-api.onrender.com/api/caption
   [API] Response - Status: 200
   ```

### Check Logs

**Render Backend Logs**:
- Dashboard → Select your service → Logs tab
- Look for: `[API]` or `[ERROR]` prefixes

**Vercel Frontend Logs**:
- Dashboard → Select your project → Deployments → Select deployment → Logs

---

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Frontend shows "Cannot connect" | Check `VITE_API_BASE_URL` in Vercel |
| CORS error in browser | Add Vercel domain to Render `CORS_ORIGINS` |
| Video upload fails | Check Gemini API key is set and valid |
| Slow uploads | Try smaller video or lower `FRAME_COUNT` |
| 404 on `/api/caption` | Verify Render backend is running |

---

## Next Steps

- **Monitoring**: Set up alerts in Render for failed deployments
- **Custom Domain**: Add custom domain to Vercel project
- **Analytics**: Enable Vercel Analytics to track performance
- **CI/CD**: Push to GitHub to trigger automatic redeployment
- **Database**: If needed, add PostgreSQL to Render for persistent storage

---

## Support

For issues:
1. Check Render logs: https://render.com/docs/logs
2. Check Vercel logs: https://vercel.com/docs/concepts/deployments/logs
3. Check Gemini API docs: https://ai.google.dev
4. GitHub Issues (if applicable)

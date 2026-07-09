# Quick Start: Deploy to Production

This is a **TL;DR** version. For full details, see `DEPLOYMENT_GUIDE.md`.

## 🚀 Deploy in 5 Minutes

### Prerequisites
- GitHub repo connected to Vercel & Render
- Gemini API key from https://aistudio.google.com

### Step 1: Render Backend (2 min)

1. Go to https://render.com/dashboard
2. Create Web Service from your GitHub repo
3. Set:
   ```
   Build: pip install -r api/requirements.txt
   Start: cd api && uvicorn main:app --host 0.0.0.0 --port 10000
   ```
4. Add Environment Variables:
   ```
   GEMINI_API_KEY=your-key-here
   ENVIRONMENT=production
   ```
5. Deploy ✓

**Get your backend URL**: `https://your-service.onrender.com`

### Step 2: Vercel Frontend (2 min)

1. Go to https://vercel.com/dashboard
2. Import your GitHub repo
3. Settings:
   ```
   Build: npm install --prefix web && npm run build --prefix web
   Output: web/dist
   ```
4. Add Environment Variable:
   ```
   VITE_API_BASE_URL=https://your-service.onrender.com
   ```
5. Deploy ✓

**Get your frontend URL**: `https://your-project.vercel.app`

### Step 3: Update Backend CORS (1 min)

1. Go back to Render dashboard
2. Edit Environment Variables
3. Add/update:
   ```
   CORS_ORIGINS=https://your-project.vercel.app
   ```
4. Render auto-redeploys ✓

## ✅ Verify

```bash
# Backend health
curl https://your-service.onrender.com/api/health
# Should return: {"status": "ok", ...}

# Frontend is up
Open https://your-project.vercel.app in browser
# Upload a test video
```

## 🔧 Environment Variables

### Render (Backend)
| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | Your actual API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | Your Vercel URL |

### Vercel (Frontend)
| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | Your Render URL |

## 🆘 Issues?

### "Cannot connect to backend"
- Check `VITE_API_BASE_URL` in Vercel environment
- Verify Render backend is running: `curl https://your-service.onrender.com/api/health`

### "CORS error"
- Check your Vercel domain is in Render's `CORS_ORIGINS`

### "Upload fails"
- Check Gemini API key is valid
- Check video is under 100MB and is MP4/WebM/MOV

**Full troubleshooting**: See `TROUBLESHOOTING.md`

## 📚 Full Guides

- **Complete Setup**: `DEPLOYMENT_GUIDE.md`
- **Issues & Fixes**: `TROUBLESHOOTING.md`
- **Pre-Launch**: `PRODUCTION_CHECKLIST.md`
- **Full Report**: `DEPLOYMENT_AUDIT_REPORT.md`

---

**Status**: Ready to deploy! 🎉

# Troubleshooting & Debugging Guide

## Frontend Issues

### Issue: Application loads but no upload zone appears

**Symptoms**: Blank page or UI doesn't render

**Diagnostics**:
1. Open browser DevTools (F12 → Console tab)
2. Look for JavaScript errors (red text)
3. Check Network tab for failed requests

**Solutions**:
- Clear browser cache: Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
- Check for CSS issues: Open DevTools → Elements tab → look for errors
- Verify Vite build completed: `npm run build` locally

---

### Issue: "Cannot connect to backend" error

**Symptoms**: Error message appears when trying to upload video

**Diagnostics**:
1. Check CORS error in browser console:
   ```
   Access to XMLHttpRequest blocked by CORS policy
   ```
2. Check network request:
   - DevTools → Network tab
   - Click on failed `/api/caption` request
   - Look at Response headers

**Solutions**:

1. **Verify backend URL** (Vercel environment variables):
   ```
   VITE_API_BASE_URL=https://video-captioning-api.onrender.com
   ```

2. **Verify CORS on backend** (Render environment variables):
   ```
   CORS_ORIGINS=https://your-vercel-domain.vercel.app
   ```

3. **Test backend directly**:
   ```bash
   curl -I https://video-captioning-api.onrender.com/api/health
   # Should return 200 OK
   ```

4. **Check Render logs**:
   - Go to Render dashboard
   - Select your service
   - Click "Logs" tab
   - Look for lines starting with `[API]`
   - Search for `CORS configured for origins`

---

### Issue: Video uploads but no results / stuck on loading

**Symptoms**: Loading spinner keeps going or times out after 15 seconds

**Diagnostics**:
1. Open DevTools → Network tab
2. Look for `POST /api/caption` request
3. Check Response tab for error details
4. Check Console tab for JavaScript errors

**Solutions**:

1. **Check backend is processing** (Render logs):
   ```
   ✓ Uploaded XXX MB to /tmp/...
   ⏳ Extracting 5 frames...
   ⏳ Calling Gemini...
   ```

2. **Verify Gemini API key**:
   ```bash
   # In Render logs, look for:
   GEMINI_API_KEY configured: true
   # If false, the API key is not set!
   ```

3. **Check video file**:
   - Size under 100MB? (Use DevTools → Network to check)
   - Format is MP4/WebM/MOV?
   - Duration under 5 minutes?

4. **Check Render logs for errors**:
   ```
   # Look for:
   ✗ Caption generation failed: ...
   # Shows the actual error
   ```

---

## Backend Issues

### Issue: `/api/health` returns error or 500

**Symptoms**: `curl https://video-captioning-api.onrender.com/api/health` fails

**Diagnostics**:
1. Check Render logs for startup errors
2. Verify environment variables are set
3. Test with: `curl -v https://video-captioning-api.onrender.com/api/health`

**Solutions**:

1. **Verify environment variables** (Render dashboard):
   - Settings → Environment → Check all vars are set
   - Restart service after changing vars

2. **Check Python dependencies**:
   ```bash
   # Locally run:
   pip install -r api/requirements.txt
   python -c "import fastapi; print('OK')"
   ```

3. **Check logs** (Render dashboard → Logs):
   ```
   # Should see:
   INFO:     Application startup complete
   INFO:     Uvicorn running on http://0.0.0.0:10000
   
   # If you see errors, copy them for debugging
   ```

---

### Issue: "Unsupported video format" error

**Symptoms**: Server rejects video with 400 error

**Solutions**:
1. Convert video to MP4:
   ```bash
   ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
   ```

2. Verify MIME type is detected correctly:
   - File → right-click Properties → verify file extension

3. Check allowed types in [api/main.py](api/main.py):
   ```python
   allowed_types = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
   ```

---

### Issue: "File too large" error

**Symptoms**: 413 Payload Too Large error

**Solutions**:
1. Compress video before uploading:
   ```bash
   ffmpeg -i input.mp4 -b:v 5M output.mp4
   ```

2. Reduce duration or resolution

3. For testing, create small test video:
   ```bash
   # Create 10-second test video
   ffmpeg -f lavfi -i testsrc=duration=10:size=320x240:rate=1 test.mp4
   ```

---

### Issue: Gemini API returns error or 429 (rate limit)

**Symptoms**: Response shows "API error" or logs show `429 Too Many Requests`

**Solutions**:
1. Wait 30 seconds before retrying (retry logic is in code)
2. Verify API key is valid:
   - Go to https://aistudio.google.com
   - Check key hasn't been revoked
   - Create new key if needed
3. Check API quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

---

## Local Development Setup

### Problem: Backend won't start locally

**Diagnostics**:
1. Check Python version: `python --version` (must be 3.11+)
2. Check pip dependencies: `pip list | grep fastapi`

**Solutions**:
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r api/requirements.txt

# Run server
cd api && uvicorn main:app --reload --port 8000
```

### Problem: Frontend dev server fails

**Solutions**:
```bash
# Install dependencies
cd web && npm install

# Start dev server
npm run dev

# If that fails, clear cache:
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## Debugging Commands

### Frontend Debugging

```javascript
// In browser console:

// Check API base URL
console.log(import.meta.env.VITE_API_BASE_URL)

// Make test API call
fetch(new URL('/api/health', import.meta.env.VITE_API_BASE_URL || location.origin))
  .then(r => r.json())
  .then(d => console.log('Backend health:', d))
  .catch(e => console.error('Backend error:', e))

// Check all environment variables
console.log(import.meta.env)
```

### Backend Debugging

```bash
# Check running services
lsof -i :10000  # Check if port 10000 is listening

# Test API health
curl -v http://localhost:8000/api/health

# Test with real data (local)
curl -X POST http://localhost:8000/api/caption \
  -F "video=@test-video.mp4"

# View logs in real-time (if running locally)
tail -f /var/log/uvicorn.log
```

### Network Debugging

```bash
# Test backend connectivity
curl -I https://video-captioning-api.onrender.com

# Test CORS headers
curl -H "Origin: https://your-vercel-domain.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  https://video-captioning-api.onrender.com/api/caption -v
```

---

## Log Analysis

### Key Log Patterns

**Success flow**:
```
[APP] Uploading video: test.mp4
[APP] Using endpoint: https://video-captioning-api.onrender.com/api/caption
[API] POST https://video-captioning-api.onrender.com/api/caption
[API] Response - Status: 200
✓ Extracted 5 frames
✓ Calling Gemini...
✓ Results saved
```

**Error flow**:
```
[API] Network Error: ...
[API] Backend health check failed: ...
✗ Caption generation failed: ...
```

**Backend success**:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:10000
✓ Uploaded 2.5MB
✓ Extracted 5 frames
✓ Gemini response received
✓ Results saved
```

---

## Still Stuck?

1. **Check error logs** (both frontend and backend)
2. **Verify environment variables** are correctly set
3. **Test with curl/Postman** to isolate frontend vs backend issues
4. **Check GitHub for similar issues** in the repository
5. **Enable verbose logging** by setting `VITE_DEBUG=true` (frontend only)

---

## Getting Help

When asking for help, provide:
1. The error message (exact text)
2. Browser console logs (F12 → Console → copy all red text)
3. Backend logs (Render dashboard → Logs → copy relevant section)
4. Steps to reproduce the issue
5. Environment info (OS, browser, video file details)

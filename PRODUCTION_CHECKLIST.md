# Production Readiness Checklist

## Pre-Deployment

### Environment Setup
- [ ] `.env.example` created with placeholder values (no real secrets)
- [ ] `.env` file exists locally with actual credentials
- [ ] `.env` is added to `.gitignore` to prevent accidental commits
- [ ] All required environment variables documented
- [ ] GEMINI_API_KEY is valid and has API quota

### Backend Configuration
- [ ] `ENVIRONMENT=production` set in Render
- [ ] `CORS_ORIGINS` includes your Vercel domain
- [ ] `api/requirements.txt` includes all dependencies
- [ ] Python 3.11+ verified
- [ ] Database migrations run (if applicable)

### Frontend Configuration
- [ ] `VITE_API_BASE_URL` set to your Render backend URL
- [ ] Build command verified: `npm run build`
- [ ] Output directory set to `web/dist`
- [ ] `web/.env.example` created (no real secrets)
- [ ] All environment variables prefixed with `VITE_`

### Code Quality
- [ ] No console.log statements left for debugging
- [ ] Error handling added throughout codebase
- [ ] API requests have timeouts set
- [ ] Response validation in place
- [ ] File size limits enforced (100MB for videos)

### Logging & Monitoring
- [ ] Backend logging configured and tested
- [ ] Frontend error logging working
- [ ] Health check endpoints responding correctly
- [ ] Render logs accessible and reviewed
- [ ] Vercel logs accessible and reviewed

---

## Deployment Verification

### Backend (Render)
- [ ] Service deployed successfully
- [ ] Health check endpoint responding:
  ```bash
  curl https://your-backend.onrender.com/api/health
  ```
- [ ] Logs show startup complete:
  ```
  INFO:     Application startup complete
  ```
- [ ] No errors in recent logs
- [ ] Environment variables visible in Render dashboard

### Frontend (Vercel)
- [ ] Build completed successfully
- [ ] Deployment logs show no errors
- [ ] Preview URL is accessible
- [ ] Environment variables set in Vercel dashboard
- [ ] `VITE_API_BASE_URL` visible in build logs

### Cross-Domain Communication
- [ ] Frontend can reach backend:
  ```bash
  curl https://your-backend.onrender.com/api/health
  ```
- [ ] CORS headers present in backend response:
  ```bash
  curl -I https://your-backend.onrender.com/api/health
  # Check for: Access-Control-Allow-Origin
  ```
- [ ] No CORS errors in browser console
- [ ] Network requests show 200/201 status

---

## Functional Testing

### Happy Path
- [ ] [ ] Open frontend in browser
- [ ] [ ] Upload a valid MP4 video (< 100MB)
- [ ] [ ] Video processes successfully
- [ ] [ ] All 4 caption styles received
- [ ] [ ] Results display correctly
- [ ] [ ] Download JSON works

### Error Handling
- [ ] [ ] Upload oversized file → 413 error with clear message
- [ ] [ ] Upload unsupported format → 400 error with clear message
- [ ] [ ] Backend offline → Network error displayed
- [ ] [ ] Invalid Gemini key → Server error displayed
- [ ] [ ] Network timeout → Appropriate error message

### Performance
- [ ] [ ] Frontend loads within 3 seconds
- [ ] [ ] Video upload progress shows
- [ ] [ ] Processing completes within 30 seconds (typical)
- [ ] [ ] No memory leaks on repeated operations
- [ ] [ ] UI remains responsive during processing

---

## Security Checklist

### Secrets Management
- [ ] No API keys in `.git` history
- [ ] `.env` never committed
- [ ] Secrets only in deployment platform environment variables
- [ ] API keys rotated if exposed
- [ ] `GEMINI_API_KEY` not logged or transmitted insecurely

### CORS & Authentication
- [ ] CORS restricted to allowed domains only
- [ ] No `allow_origins=["*"]` in production
- [ ] Frontend cannot access sensitive endpoints
- [ ] Rate limiting considered (if using free Render tier)

### Input Validation
- [ ] File size limit enforced (100MB)
- [ ] File type validation working
- [ ] Video frames validated before Gemini call
- [ ] Response validation prevents crashes

---

## Monitoring & Maintenance

### Logging
- [ ] [ ] Backend logs contain timestamped entries
- [ ] [ ] Error stack traces present in logs
- [ ] [ ] Sensitive data (API keys) never logged
- [ ] [ ] Log rotation configured (if applicable)

### Uptime
- [ ] [ ] Health check endpoint monitors backend
- [ ] [ ] Vercel deployment status monitored
- [ ] [ ] Render service status monitored
- [ ] [ ] Alerts set up for deployment failures (optional)

### Performance
- [ ] [ ] Response times tracked
- [ ] [ ] Error rates monitored
- [ ] [ ] Gemini API quota monitored
- [ ] [ ] Database performance baseline established (if applicable)

---

## Documentation
- [ ] [ ] `DEPLOYMENT_GUIDE.md` complete and accurate
- [ ] [ ] `TROUBLESHOOTING.md` covers common issues
- [ ] [ ] Environment variables documented
- [ ] [ ] API endpoints documented
- [ ] [ ] README.md updated with production info

---

## Post-Deployment

### Monitoring (First 24 Hours)
- [ ] Check Render logs for errors
- [ ] Check Vercel logs for errors
- [ ] Monitor error rates in browser console
- [ ] Test from different browsers/networks
- [ ] Monitor API quota usage

### Optimization
- [ ] [ ] Review slow requests
- [ ] [ ] Optimize image serving
- [ ] [ ] Check bundle size
- [ ] [ ] Consider caching strategies
- [ ] [ ] Review database queries (if applicable)

### Communication
- [ ] [ ] Update status page (if applicable)
- [ ] [ ] Notify users of production URL
- [ ] [ ] Document support contacts
- [ ] [ ] Set up feedback channel

---

## Rollback Plan

- [ ] Previous deployment tagged/documented
- [ ] Rollback procedure documented
- [ ] Environment variables backed up
- [ ] Database backups created (if applicable)
- [ ] Team knows rollback procedure

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA | | | |
| DevOps | | | |
| Product Owner | | | |

---

## Notes

Use this space to document any special notes or deviations from the checklist:

```
[Deployment notes go here]
```

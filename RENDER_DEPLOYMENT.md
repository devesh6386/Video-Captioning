# Render Deployment Configuration
# This file guides deployment of the FastAPI backend to Render
# 
# Setup Instructions:
# 1. Create a new Web Service on Render
# 2. Connect your GitHub repository
# 3. Use these settings:

# Build Command (runs during deployment)
# cd api && pip install -r requirements.txt

# Start Command (runs the server)
# cd api && uvicorn main:app --host 0.0.0.0 --port 10000

# Environment Variables (set these in Render dashboard):
GEMINI_API_KEY=<set-in-render-dashboard>
GEMINI_MODEL=gemini-2.5-flash
FRAME_COUNT=5
ENABLE_SCENE_DETECTION=true
ENVIRONMENT=production
CORS_ORIGINS=https://your-vercel-app.vercel.app

# Dockerfile (alternative - if using Docker):
# FROM python:3.11-slim
# RUN apt-get update && apt-get install -y ffmpeg libgl1 libglib2.0-0
# WORKDIR /app
# COPY api/requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "10000"]

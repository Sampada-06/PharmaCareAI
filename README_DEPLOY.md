# Deployment Guide: AI Pharmacist App

This project consists of a **FastAPI backend** and a **Static HTML/CSS/JS frontend**.

## 1. Backend Deployment (FastAPI)
- **Host on**: Render, Railway, or any VPS.
- **Commands**:
  - Install dependencies: `pip install -r requirements.txt` (Make sure to generate this!)
  - Run server: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Database**: Ensure your Supabase/SQL connection strings are set in environment variables.

## 2. Frontend Deployment (Static Files)
- **Host on**: Vercel, Netlify, or GitHub Pages.
- **Config**:
  - Since this uses static files, you just need to upload the `frontend/` folder.
  - **CRITICAL**: Update the `API_BASE` in `frontend/services/api.js` to point to your deployed backend URL instead of `localhost:8001`.

## 3. Local Development
- Run `npm start` in the root folder to start both.
- Or use the `START_PHARMACY.bat` file.

## Project Structure
- `/backend`: FastAPI Python code.
- `/frontend`: HTML/CSS/JS UI code.
- `/archive`: Contains the React/Node versions if you wish to revisit them.

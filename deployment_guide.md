# Deployment Guide

## Backend on Render

1. Push this project to GitHub.
2. Create a new Render Web Service.
3. Select the `backend` folder as root directory.
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variable:

```txt
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
FRONTEND_ORIGIN=*
```

## Frontend on Netlify

1. Upload the `frontend` folder to Netlify.
2. After backend deployment, open `frontend/script.js`.
3. Replace:

```js
const API_BASE = "http://127.0.0.1:8000";
```

With your Render backend URL.

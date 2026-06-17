# OpenIMS PDF Chatbot

FastAPI + HTML/CSS/JS + Groq Cloud + ChromaDB PDF chatbot.

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your Groq API key in `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Run backend:

```bash
python -m uvicorn main:app --reload
```

Backend opens at:

```txt
http://127.0.0.1:8000
```

## Frontend setup

Open another terminal:

```bash
cd frontend
python -m http.server 5500
```

Open:

```txt
http://127.0.0.1:5500
```

## Replace icon

Replace this file with your own image:

```txt
frontend/assets/bot_icon.svg
```

If you use PNG/JPG, update image path in `index.html` and `script.js`.

## Deployment

Backend: Render / Railway
Frontend: Netlify / Vercel

For deployed frontend, change `API_BASE` in `frontend/script.js` to your backend URL.

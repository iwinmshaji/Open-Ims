import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from rag import UPLOAD_DIR, store_pdf, search_context, list_uploaded_pdfs, reset_database

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")

app = FastAPI(title="OpenIMS PDF Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "message": "OpenIMS PDF Chatbot API Running"
    }


@app.get("/documents")
def documents():
    return {
        "documents": list_uploaded_pdfs()
    }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_path = UPLOAD_DIR / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = store_pdf(str(file_path), file.filename)

    if not result["stored"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/chat")
def chat(request: ChatRequest):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq API key missing.")

    question = request.message.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Message is empty.")

    retrieved = search_context(question)

    if not retrieved["context"]:
        return {
            "answer": "Please upload and store a PDF first. Then I can answer from it.",
            "sources": []
        }

    prompt = f"""
You are OpenIMS, a helpful PDF chatbot.

Answer the user's question using ONLY the PDF context below.
If the answer is not inside the PDF context, say:
"I could not find that information in the uploaded PDF."

Be clear, simple, and human-like.

PDF Context:
{retrieved["context"]}

User Question:
{question}
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are OpenIMS, a PDF question-answering assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=700,
        )

        answer = response.choices[0].message.content

        return {
            "answer": answer,
            "sources": retrieved["sources"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/reset")
def reset():
    reset_database()

    for file in UPLOAD_DIR.glob("*.pdf"):
        file.unlink()

    return {
        "message": "Database and uploaded PDFs cleared."
    }
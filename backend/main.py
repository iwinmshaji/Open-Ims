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

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

app = FastAPI(title="OpenIMS PDF Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {"message": "OpenIMS PDF Chatbot Backend Running"}


@app.get("/documents")
def documents():
    return {"documents": list_uploaded_pdfs()}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    safe_name = Path(file.filename).name
    save_path = UPLOAD_DIR / safe_name

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = store_pdf(str(save_path), safe_name)
    if not result.get("stored"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if not groq_client:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing. Add it inside backend/.env")

    retrieved = search_context(req.message)
    context = retrieved["context"]

    if not context:
        return {
            "answer": "Please upload a PDF first. I can answer only from the stored PDF documents.",
            "sources": [],
        }

    system_prompt = """
You are OpenIMS, a helpful and human-like PDF chatbot.
Answer only using the provided PDF context.
If the answer is not found in the context, say: "I could not find that information in the uploaded PDF."
Keep answers clear, friendly, and useful.
Do not invent information.
Mention source page numbers when helpful.
"""

    user_prompt = f"""
PDF Context:
{context}

User question:
{req.message}
"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=900,
    )

    answer = response.choices[0].message.content
    return {"answer": answer, "sources": retrieved["sources"]}


@app.delete("/reset")
def reset():
    reset_database()
    for pdf in UPLOAD_DIR.glob("*.pdf"):
        pdf.unlink()
    return {"message": "All uploaded PDFs and vector data removed."}

import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "openims_pdf_docs"

UPLOAD_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

client = None
collection = None
embedding_function = None


def get_collection():
    global client, collection, embedding_function

    if collection is None:
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    return collection


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or " ").strip()
    return text


def extract_pdf_text(file_path: str) -> List[Dict[str, Any]]:
    reader = PdfReader(file_path)
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append({"page": i, "text": text})

    return pages


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def store_pdf(file_path: str, original_filename: str) -> Dict[str, Any]:
    db = get_collection()

    pages = extract_pdf_text(file_path)

    if not pages:
        return {
            "stored": False,
            "message": "No readable text found in this PDF.",
        }

    ids, docs, metas = [], [], []
    doc_id = str(uuid.uuid4())

    for page in pages:
        chunks = chunk_text(page["text"])

        for chunk_index, chunk in enumerate(chunks):
            ids.append(f"{doc_id}_{page['page']}_{chunk_index}")
            docs.append(chunk)
            metas.append(
                {
                    "doc_id": doc_id,
                    "filename": original_filename,
                    "page": page["page"],
                    "chunk_index": chunk_index,
                }
            )

    db.add(ids=ids, documents=docs, metadatas=metas)

    return {
        "stored": True,
        "filename": original_filename,
        "doc_id": doc_id,
        "pages": len(pages),
        "chunks": len(docs),
    }


def search_context(question: str, n_results: int = 5) -> Dict[str, Any]:
    db = get_collection()

    total = db.count()

    if total == 0:
        return {"context": "", "sources": []}

    result = db.query(
        query_texts=[question],
        n_results=min(n_results, total),
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    context_parts = []
    sources = []

    for doc, meta in zip(documents, metadatas):
        context_parts.append(
            f"Source: {meta.get('filename')} | Page: {meta.get('page')}\n{doc}"
        )

        sources.append(
            {
                "filename": meta.get("filename"),
                "page": meta.get("page"),
            }
        )

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "sources": sources,
    }


def list_uploaded_pdfs() -> List[str]:
    return sorted([p.name for p in UPLOAD_DIR.glob("*.pdf")])


def reset_database() -> None:
    global client, collection, embedding_function

    db = get_collection()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
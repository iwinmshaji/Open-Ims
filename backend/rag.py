import re
import uuid
import hashlib
import math
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "openims_pdf_docs"

UPLOAD_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)


class SimpleHashEmbeddingFunction(EmbeddingFunction):
    def name(self):
        return "simple_hash_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []

        for text in input:
            vector = [0.0] * 384
            words = re.findall(r"\w+", text.lower())

            for word in words:
                index = int(hashlib.md5(word.encode()).hexdigest(), 16) % 384
                vector[index] += 1.0

            norm = math.sqrt(sum(x * x for x in vector))

            if norm > 0:
                vector = [x / norm for x in vector]

            embeddings.append(vector)

        return embeddings


embedding_function = SimpleHashEmbeddingFunction()
client = chromadb.PersistentClient(path=str(CHROMA_DIR))


try:
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
except Exception:
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_pdf_text(file_path: str) -> List[Dict[str, Any]]:
    reader = PdfReader(file_path)
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")

        if text:
            pages.append({
                "page": i,
                "text": text
            })

    return pages


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def store_pdf(file_path: str, original_filename: str) -> Dict[str, Any]:
    pages = extract_pdf_text(file_path)

    if not pages:
        return {
            "stored": False,
            "message": "No readable text found in this PDF."
        }

    doc_id = str(uuid.uuid4())
    ids = []
    docs = []
    metas = []

    for page in pages:
        chunks = chunk_text(page["text"])

        for index, chunk in enumerate(chunks):
            ids.append(f"{doc_id}_{page['page']}_{index}")
            docs.append(chunk)
            metas.append({
                "doc_id": doc_id,
                "filename": original_filename,
                "page": page["page"],
                "chunk_index": index,
            })

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metas
    )

    return {
        "stored": True,
        "filename": original_filename,
        "doc_id": doc_id,
        "pages": len(pages),
        "chunks": len(docs),
    }


def search_context(question: str, n_results: int = 5) -> Dict[str, Any]:
    total = collection.count()

    if total == 0:
        return {
            "context": "",
            "sources": []
        }

    result = collection.query(
        query_texts=[question],
        n_results=min(n_results, total)
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    context_parts = []
    sources = []

    for doc, meta in zip(documents, metadatas):
        context_parts.append(
            f"Source: {meta.get('filename')} | Page: {meta.get('page')}\n{doc}"
        )

        sources.append({
            "filename": meta.get("filename"),
            "page": meta.get("page")
        })

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "sources": sources
    }


def list_uploaded_pdfs() -> List[str]:
    return sorted([p.name for p in UPLOAD_DIR.glob("*.pdf")])


def reset_database() -> None:
    global collection

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
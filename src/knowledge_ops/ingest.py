"""Ingest enterprise documents into a local Chroma vector store."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import chromadb

from knowledge_ops.config import Settings, get_settings
from knowledge_ops.llm import get_embeddings


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        # prefer breaking on paragraph/newline
        if end < len(text):
            window = text[start:end]
            break_at = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
            if break_at > chunk_size * 0.4:
                end = start + break_at + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _doc_id(source: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{source}:{index}:{text[:64]}".encode()).hexdigest()[:12]
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", source)
    return f"{safe}__{index}__{digest}"


def load_documents(docs_dir: Path) -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    if not docs_dir.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")
    for path in sorted(docs_dir.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        docs.append((path.name, path.read_text(encoding="utf-8")))
    return docs


def get_chroma_collection(settings: Settings | None = None):
    settings = settings or get_settings()
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_or_create_collection(name=settings.collection_name)


def ingest_documents(settings: Settings | None = None, reset: bool = False) -> dict[str, Any]:
    settings = settings or get_settings()
    docs = load_documents(settings.docs_dir)
    embeddings = get_embeddings(settings)

    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    if reset:
        try:
            client.delete_collection(settings.collection_name)
        except Exception:
            pass
    collection = client.get_or_create_collection(name=settings.collection_name)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for source, content in docs:
        for i, chunk in enumerate(
            _chunk_text(content, settings.chunk_size, settings.chunk_overlap)
        ):
            ids.append(_doc_id(source, i, chunk))
            texts.append(chunk)
            metadatas.append({"source": source, "chunk_index": i})

    if not texts:
        return {"documents": 0, "chunks": 0, "collection": settings.collection_name}

    vectors = embeddings.embed_documents(texts)
    # upsert in batches
    batch = 64
    for start in range(0, len(texts), batch):
        end = start + batch
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            embeddings=vectors[start:end],
            metadatas=metadatas[start:end],
        )

    return {
        "documents": len(docs),
        "chunks": len(texts),
        "collection": settings.collection_name,
        "chroma_dir": str(settings.chroma_dir),
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    reset = "--reset" in argv
    result = ingest_documents(reset=reset)
    print(
        f"Ingested {result['documents']} documents → {result['chunks']} chunks "
        f"into {result['collection']} ({result.get('chroma_dir')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

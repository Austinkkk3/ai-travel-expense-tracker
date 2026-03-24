"""
astra_helper.py
Uploads Streamlit-uploaded PDF files to DataStax Astra DB for RAG retrieval.
Called automatically after expense processing in app.py.
"""

import os
import tempfile
from dotenv import load_dotenv

load_dotenv()


def _get_collection():
    from astrapy import DataAPIClient
    token    = os.getenv("ASTRA_TOKEN")
    endpoint = os.getenv("ASTRA_ENDPOINT")
    name     = os.getenv("ASTRA_COLLECTION", "receipts")
    if not token or not endpoint:
        raise ValueError("ASTRA_TOKEN and ASTRA_ENDPOINT must be set in .env")
    db = DataAPIClient(token).get_database_by_api_endpoint(endpoint)
    return db.get_collection(name)


def _chunk_text(text: str, size: int = 1000) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def upload_files_to_astra(uploaded_files) -> int:
    """
    Convert each Streamlit UploadedFile to Markdown via Docling,
    chunk it, and store in Astra DB.

    Returns the total number of chunks uploaded.
    """
    from docling.document_converter import DocumentConverter

    converter  = DocumentConverter()
    collection = _get_collection()
    total      = 0

    for f in uploaded_files:
        # Write bytes to a temp file so Docling can read it
        # seek(0) first — process_invoices() may have already consumed the stream
        f.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(f.read())
            tmp_path = tmp.name

        try:
            result   = converter.convert(tmp_path)
            markdown = result.document.export_to_markdown()
            chunks   = _chunk_text(markdown)

            docs = [
                {"content": chunk, "source": f.name, "chunk": i}
                for i, chunk in enumerate(chunks)
            ]
            if docs:
                collection.insert_many(docs)
            total += len(chunks)
        finally:
            os.unlink(tmp_path)
            f.seek(0)   # reset pointer so the file can be re-read later

    return total

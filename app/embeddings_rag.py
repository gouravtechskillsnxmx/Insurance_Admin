import os, openai, chromadb
from chromadb.config import Settings

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
CHROMA_URL = os.getenv("CHROMA_SERVER_URL", "http://localhost:8000")

def get_embeddings(texts):
    resp = openai.Embedding.create(model=OPENAI_MODEL, input=texts)
    return [d['embedding'] for d in resp['data']]

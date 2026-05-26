import hashlib
import math

from openai import OpenAI

from app.config import settings


VECTOR_SIZE = 768


def create_local_embedding(text: str) -> list[float]:
    """
    Create a deterministic 768-dimensional vector from text.

    This is a lightweight local fallback embedding.
    It lets the backend keep working even without OpenAI.
    """
    if not text.strip():
        text = "empty"

    vector = [0.0] * VECTOR_SIZE
    words = text.lower().split()

    for word in words:
        word_hash = hashlib.sha256(word.encode("utf-8")).digest()

        for index, byte in enumerate(word_hash):
            vector_index = index % VECTOR_SIZE
            vector[vector_index] += byte / 255.0

    magnitude = math.sqrt(sum(value * value for value in vector))

    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]


def create_openai_embedding(text: str) -> list[float]:
    """
    Create a 768-dimensional embedding using OpenAI.

    Required .env values:
    OPENAI_API_KEY=...
    OPENAI_EMBEDDING_MODEL=text-embedding-3-small
    EMBEDDING_PROVIDER=openai
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is missing in .env")

    if not text.strip():
        text = "empty"

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
        dimensions=VECTOR_SIZE,
    )

    return response.data[0].embedding


def create_embedding(text: str) -> list[float]:
    """
    Create an embedding using the configured provider.

    EMBEDDING_PROVIDER=openai uses OpenAI embeddings.
    Any other value falls back to the local deterministic embedding.
    """
    embedding_provider = getattr(settings, "embedding_provider", "local")

    if embedding_provider == "openai":
        return create_openai_embedding(text)

    return create_local_embedding(text)

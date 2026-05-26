from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from app.config import settings
from app.embeddings import VECTOR_SIZE, create_embedding


def get_qdrant_client() -> QdrantClient:
    """
    Create a Qdrant client using values from .env.
    """
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def ensure_collection_exists() -> bool:
    """
    Create the Qdrant collection if it does not already exist.
    This collection stores course-content embeddings for RAG.
    """
    client = get_qdrant_client()

    existing_collections = client.get_collections().collections
    existing_names = [collection.name for collection in existing_collections]

    if settings.qdrant_collection not in existing_names:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    return True


def check_qdrant_connection() -> bool:
    """
    Simple health check for Qdrant.
    Returns True if Qdrant responds.
    """
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception as error:
        print(f"Qdrant connection failed: {error}")
        return False


def build_metadata_filter(
    subject: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    difficulty: int | None = None,
    lang: str | None = None,
    tags: list[str] | None = None,
) -> Filter | None:
    """
    Build a Qdrant payload filter from optional metadata fields.

    Filtering rules:
    - subject: exact match
    - topic: exact match
    - subtopic: exact match
    - difficulty: max difficulty filter, meaning stored difficulty <= requested difficulty
    - lang: exact match
    - tags: match any requested tag

    If no filters are provided, return None.
    """
    conditions = []

    if subject:
        conditions.append(
            FieldCondition(
                key="subject",
                match=MatchValue(value=subject),
            )
        )

    if topic:
        conditions.append(
            FieldCondition(
                key="topic",
                match=MatchValue(value=topic),
            )
        )

    if subtopic:
        conditions.append(
            FieldCondition(
                key="subtopic",
                match=MatchValue(value=subtopic),
            )
        )

    if difficulty is not None:
        conditions.append(
            FieldCondition(
                key="difficulty",
                range=Range(lte=difficulty),
            )
        )

    if lang:
        conditions.append(
            FieldCondition(
                key="lang",
                match=MatchValue(value=lang),
            )
        )

    if tags:
        conditions.append(
            FieldCondition(
                key="tags",
                match=MatchAny(any=tags),
            )
        )

    if not conditions:
        return None

    return Filter(must=conditions)


def store_document_vector(
    title: str,
    content: str,
    source: str | None = None,
) -> str:
    """
    Create an embedding for a document and store it in Qdrant.
    Returns the Qdrant point ID.

    This supports the original simple /documents endpoint.
    """
    client = get_qdrant_client()
    point_id = str(uuid4())

    embedding = create_embedding(f"{title}\n{content}")

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "document",
                    "title": title,
                    "content": content,
                    "source": source,
                },
            )
        ],
    )

    return point_id


def store_chunk_vector(
    title: str,
    content: str,
    document_id: int,
    chunk_index: int,
    source: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    difficulty: int | None = None,
    lang: str | None = "en",
    page: int | None = None,
    tags: list[str] | None = None,
) -> str:
    """
    Create an embedding for one document chunk and store it in Qdrant.
    Returns the Qdrant point ID.
    """
    client = get_qdrant_client()
    point_id = str(uuid4())
    safe_tags = tags or []

    embedding = create_embedding(f"{title}\n{content}")

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "chunk",
                    "title": title,
                    "content": content,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "chunk_id": point_id,
                    "source": source,
                    "subject": subject,
                    "topic": topic,
                    "subtopic": subtopic,
                    "difficulty": difficulty,
                    "lang": lang,
                    "page": page,
                    "tags": safe_tags,
                },
            )
        ],
    )

    return point_id


def search_document_vectors(
    query: str,
    limit: int = 5,
    subject: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    difficulty: int | None = None,
    lang: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """
    Search Qdrant for documents/chunks similar to the query.
    Optional metadata filters narrow results by course metadata.
    Returns matching payloads with similarity scores.
    """
    client = get_qdrant_client()
    query_embedding = create_embedding(query)

    metadata_filter = build_metadata_filter(
        subject=subject,
        topic=topic,
        subtopic=subtopic,
        difficulty=difficulty,
        lang=lang,
        tags=tags,
    )

    search_response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        query_filter=metadata_filter,
        limit=limit,
    )

    search_results = search_response.points
    results = []

    for item in search_results:
        payload = item.payload or {}

        results.append(
            {
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "source": payload.get("source"),
                "score": item.score,
                "subject": payload.get("subject"),
                "topic": payload.get("topic"),
                "subtopic": payload.get("subtopic"),
                "difficulty": payload.get("difficulty"),
                "lang": payload.get("lang"),
                "page": payload.get("page"),
                "chunk_id": payload.get("chunk_id"),
                "tags": payload.get("tags") or [],
            }
        )

    return results


def delete_vectors_by_point_ids(point_ids: list[str]) -> bool:
    """
    Delete Qdrant vectors by point IDs.

    Used by admin content edit/delete so removed content does not keep
    appearing in RAG search results.
    """
    if not point_ids:
        return True

    client = get_qdrant_client()

    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=point_ids,
    )

    return True


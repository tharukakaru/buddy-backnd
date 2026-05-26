from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_admin
from app.chunking import split_text_into_chunks
from app.config import settings
from app.database_init import create_tables
from app.db import (
    check_database_connection,
    delete_document_by_id,
    delete_document_chunks,
    get_admin_content_detail,
    get_admin_content_list,
    get_document_qdrant_point_ids,
    get_progress_by_subject,
    get_progress_dashboard,
    get_progress_recommendations,
    get_progress_summary,
    get_recent_events,
    get_recent_questions,
    get_weak_areas,
    insert_document,
    insert_document_chunk,
    insert_event_log,
    update_document_base,
)
from app.file_extractors import extract_text_from_upload
from app.llm import generate_answer
from app.schemas import (
    AdminContentCreate,
    AdminContentDetail,
    AdminContentMutationResponse,
    AdminContentSummary,
    AdminContentUpdate,
    AskRequest,
    AskResponse,
    DocumentCreate,
    DocumentResponse,
    SearchRequest,
    SearchResult,
    TextIngestRequest,
    TextIngestResponse,
)
from app.vector_store import (
    check_qdrant_connection,
    delete_vectors_by_point_ids,
    ensure_collection_exists,
    search_document_vectors,
    store_chunk_vector,
    store_document_vector,
)

app = FastAPI(title=settings.app_name)

# Allow frontend (localhost:8080 dev + any hosted domain) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """
    Runs when the API starts.
    Ensures PostgreSQL tables and Qdrant collection exist before requests come in.
    """
    create_tables()
    ensure_collection_exists()


@app.get("/")
def root():
    return {
        "message": "Buddy AI Backend is running",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/health")
def health_check():
    postgres_ok = check_database_connection()
    qdrant_ok = check_qdrant_connection()

    return {
        "status": "ok" if postgres_ok and qdrant_ok else "error",
        "services": {
            "postgres": postgres_ok,
            "qdrant": qdrant_ok,
        },
    }


@app.get("/events/recent")
def read_recent_events(limit: int = 10):
    """
    Read recent backend activity events from PostgreSQL.
    """
    return get_recent_events(limit=limit)


@app.get("/progress/summary")
def read_progress_summary():
    """
    Read a simple learning progress summary from PostgreSQL events.
    """
    return get_progress_summary()


@app.get("/progress/by-subject")
def read_progress_by_subject():
    """
    Read progress grouped by subject, topic, and subtopic.
    """
    return get_progress_by_subject()


@app.get("/progress/recent-questions")
def read_recent_questions(limit: int = 10):
    """
    Read recent student questions in a clean progress-friendly format.
    """
    return get_recent_questions(limit=limit)


@app.get("/progress/weak-areas")
def read_weak_areas():
    """
    Read weak retrieval areas from PostgreSQL events.
    """
    return get_weak_areas()


@app.get("/progress/recommendations")
def read_progress_recommendations():
    """
    Generate study recommendations from progress data.

    This uses:
    - weak areas
    - recent questions
    - fallback starter recommendation
    """
    return get_progress_recommendations()


@app.get("/progress/me")
def read_my_progress():
    """
    Combined student progress dashboard endpoint.

    This returns:
    - progress summary
    - progress by subject
    - recent questions
    - weak areas
    - recommendations

    This endpoint is useful for frontend and n8n because it gives the main
    progress data in one request.
    """
    return get_progress_dashboard()


@app.post("/documents", response_model=DocumentResponse)
def create_document(document: DocumentCreate):
    """
    Save a document in PostgreSQL and store its vector in Qdrant.

    This is the original simple ingestion endpoint.
    """
    qdrant_point_id = store_document_vector(
        title=document.title,
        content=document.content,
        source=document.source,
    )

    saved_document = insert_document(
        title=document.title,
        content=document.content,
        source=document.source,
        qdrant_point_id=qdrant_point_id,
    )

    return saved_document


@app.post("/ingest/text", response_model=TextIngestResponse)
def ingest_text(request: TextIngestRequest):
    """
    Ingest long text using chunking + metadata.

    Flow:
    - save the original document in PostgreSQL
    - split content into chunks
    - store each chunk vector in Qdrant
    - store each chunk row in PostgreSQL
    """
    saved_document = insert_document(
        title=request.title,
        content=request.content,
        source=request.source,
        qdrant_point_id=None,
    )

    document_id = saved_document["id"]

    chunks = split_text_into_chunks(
        text=request.content,
        chunk_size=700,
        overlap=100,
    )

    qdrant_point_ids = []

    for chunk_index, chunk_content in enumerate(chunks):
        qdrant_point_id = store_chunk_vector(
            title=request.title,
            content=chunk_content,
            document_id=document_id,
            chunk_index=chunk_index,
            source=request.source,
            subject=request.subject,
            topic=request.topic,
            subtopic=request.subtopic,
            difficulty=request.difficulty,
            lang=request.lang,
            page=request.page,
            tags=request.tags,
        )

        insert_document_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_id=qdrant_point_id,
            content=chunk_content,
            source=request.source,
            subject=request.subject,
            topic=request.topic,
            subtopic=request.subtopic,
            difficulty=request.difficulty,
            lang=request.lang,
            page=request.page,
            tags=request.tags,
            qdrant_point_id=qdrant_point_id,
        )

        qdrant_point_ids.append(qdrant_point_id)

    return {
        "document_id": document_id,
        "title": request.title,
        "source": request.source,
        "chunk_count": len(chunks),
        "qdrant_point_ids": qdrant_point_ids,
    }


@app.post("/ingest/file", response_model=TextIngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    topic: str | None = Form(default=None),
    subtopic: str | None = Form(default=None),
    difficulty: int | None = Form(default=None),
    lang: str | None = Form(default="en"),
    page: int | None = Form(default=None),
    tags: str | None = Form(default=None),
):
    """
    Ingest an uploaded learning-content file into the RAG pipeline.

    Supported file types:
    - .txt
    - .md
    - .pdf
    - .docx

    Tags should be sent as a comma-separated string:
    robotics,sensor,arduino
    """
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted_text = extract_text_from_upload(
            filename=file.filename or "",
            file_bytes=file_bytes,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No readable text was extracted from the uploaded file.",
        )

    safe_title = title or file.filename or "uploaded-content"
    safe_source = source or file.filename

    parsed_tags = []
    if tags:
        parsed_tags = [
            tag.strip()
            for tag in tags.split(",")
            if tag.strip()
        ]

    saved_document = insert_document(
        title=safe_title,
        content=extracted_text,
        source=safe_source,
        qdrant_point_id=None,
    )

    document_id = saved_document["id"]

    chunks = split_text_into_chunks(
        text=extracted_text,
        chunk_size=700,
        overlap=100,
    )

    qdrant_point_ids = []

    for chunk_index, chunk_content in enumerate(chunks):
        qdrant_point_id = store_chunk_vector(
            title=safe_title,
            content=chunk_content,
            document_id=document_id,
            chunk_index=chunk_index,
            source=safe_source,
            subject=subject,
            topic=topic,
            subtopic=subtopic,
            difficulty=difficulty,
            lang=lang,
            page=page,
            tags=parsed_tags,
        )

        insert_document_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_id=qdrant_point_id,
            content=chunk_content,
            source=safe_source,
            subject=subject,
            topic=topic,
            subtopic=subtopic,
            difficulty=difficulty,
            lang=lang,
            page=page,
            tags=parsed_tags,
            qdrant_point_id=qdrant_point_id,
        )

        qdrant_point_ids.append(qdrant_point_id)

    return {
        "document_id": document_id,
        "title": safe_title,
        "source": safe_source,
        "chunk_count": len(chunks),
        "qdrant_point_ids": qdrant_point_ids,
    }


@app.get("/admin/content", response_model=list[AdminContentSummary])
def list_admin_content(
    limit: int = 20,
    offset: int = 0,
    _: None = Depends(require_admin),
):
    """
    Admin endpoint: list uploaded/ingested learning content.

    Requires header:
    X-User-Role: admin
    """
    return get_admin_content_list(limit=limit, offset=offset)


@app.get("/admin/content/{document_id}", response_model=AdminContentDetail)
def read_admin_content(
    document_id: int,
    _: None = Depends(require_admin),
):
    """
    Admin endpoint: read one document and its chunks.

    Requires header:
    X-User-Role: admin
    """
    content = get_admin_content_detail(document_id=document_id)

    if not content:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id {document_id} was not found.",
        )

    return content


@app.post("/admin/content", response_model=AdminContentMutationResponse)
def create_admin_content(
    request: AdminContentCreate,
    _: None = Depends(require_admin),
):
    """
    Admin endpoint: add new learning content.

    Flow:
    - save document in PostgreSQL
    - split content into chunks
    - store chunk vectors in Qdrant
    - store chunk metadata in PostgreSQL

    Requires header:
    X-User-Role: admin
    """
    saved_document = insert_document(
        title=request.title,
        content=request.content,
        source=request.source,
        qdrant_point_id=None,
    )

    document_id = saved_document["id"]

    chunks = split_text_into_chunks(
        text=request.content,
        chunk_size=700,
        overlap=100,
    )

    qdrant_point_ids = []

    for chunk_index, chunk_content in enumerate(chunks):
        qdrant_point_id = store_chunk_vector(
            title=request.title,
            content=chunk_content,
            document_id=document_id,
            chunk_index=chunk_index,
            source=request.source,
            subject=request.subject,
            topic=request.topic,
            subtopic=request.subtopic,
            difficulty=request.difficulty,
            lang=request.lang,
            page=request.page,
            tags=request.tags,
        )

        insert_document_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_id=qdrant_point_id,
            content=chunk_content,
            source=request.source,
            subject=request.subject,
            topic=request.topic,
            subtopic=request.subtopic,
            difficulty=request.difficulty,
            lang=request.lang,
            page=request.page,
            tags=request.tags,
            qdrant_point_id=qdrant_point_id,
        )

        qdrant_point_ids.append(qdrant_point_id)

    return {
        "document_id": document_id,
        "title": request.title,
        "source": request.source,
        "chunk_count": len(chunks),
        "qdrant_point_ids": qdrant_point_ids,
        "message": "Admin content created successfully.",
    }


@app.patch("/admin/content/{document_id}", response_model=AdminContentMutationResponse)
def update_admin_content(
    document_id: int,
    request: AdminContentUpdate,
    _: None = Depends(require_admin),
):
    """
    Admin endpoint: edit existing learning content.

    Important:
    RAG content exists in both PostgreSQL and Qdrant.
    So editing content must:
    - read existing document
    - delete old Qdrant vectors
    - delete old PostgreSQL chunks
    - update document row
    - re-chunk new content
    - store new Qdrant vectors
    - store new PostgreSQL chunks

    Requires header:
    X-User-Role: admin
    """
    existing_content = get_admin_content_detail(document_id=document_id)

    if not existing_content:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id {document_id} was not found.",
        )

    updated_title = request.title if request.title is not None else existing_content["title"]
    updated_content = request.content if request.content is not None else existing_content["content"]
    updated_source = request.source if request.source is not None else existing_content["source"]

    existing_chunks = existing_content.get("chunks", [])
    first_chunk = existing_chunks[0] if existing_chunks else {}

    updated_subject = request.subject if request.subject is not None else first_chunk.get("subject")
    updated_topic = request.topic if request.topic is not None else first_chunk.get("topic")
    updated_subtopic = request.subtopic if request.subtopic is not None else first_chunk.get("subtopic")
    updated_difficulty = request.difficulty if request.difficulty is not None else first_chunk.get("difficulty")
    updated_lang = request.lang if request.lang is not None else first_chunk.get("lang") or "en"
    updated_page = request.page if request.page is not None else first_chunk.get("page")
    updated_tags = request.tags if request.tags is not None else first_chunk.get("tags") or []

    old_qdrant_point_ids = get_document_qdrant_point_ids(document_id=document_id)
    delete_vectors_by_point_ids(point_ids=old_qdrant_point_ids)

    delete_document_chunks(document_id=document_id)

    updated_document = update_document_base(
        document_id=document_id,
        title=updated_title,
        content=updated_content,
        source=updated_source,
        qdrant_point_id=None,
    )

    if not updated_document:
        raise HTTPException(
            status_code=500,
            detail="Failed to update document row.",
        )

    chunks = split_text_into_chunks(
        text=updated_content,
        chunk_size=700,
        overlap=100,
    )

    qdrant_point_ids = []

    for chunk_index, chunk_content in enumerate(chunks):
        qdrant_point_id = store_chunk_vector(
            title=updated_title,
            content=chunk_content,
            document_id=document_id,
            chunk_index=chunk_index,
            source=updated_source,
            subject=updated_subject,
            topic=updated_topic,
            subtopic=updated_subtopic,
            difficulty=updated_difficulty,
            lang=updated_lang,
            page=updated_page,
            tags=updated_tags,
        )

        insert_document_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_id=qdrant_point_id,
            content=chunk_content,
            source=updated_source,
            subject=updated_subject,
            topic=updated_topic,
            subtopic=updated_subtopic,
            difficulty=updated_difficulty,
            lang=updated_lang,
            page=updated_page,
            tags=updated_tags,
            qdrant_point_id=qdrant_point_id,
        )

        qdrant_point_ids.append(qdrant_point_id)

    return {
        "document_id": document_id,
        "title": updated_title,
        "source": updated_source,
        "chunk_count": len(chunks),
        "qdrant_point_ids": qdrant_point_ids,
        "message": "Admin content updated successfully.",
    }


@app.delete("/admin/content/{document_id}")
def delete_admin_content(
    document_id: int,
    _: None = Depends(require_admin),
):
    """
    Admin endpoint: delete learning content.

    Important:
    Delete from both Qdrant and PostgreSQL so deleted content does not appear
    in future search/ask results.

    Requires header:
    X-User-Role: admin
    """
    existing_content = get_admin_content_detail(document_id=document_id)

    if not existing_content:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id {document_id} was not found.",
        )

    qdrant_point_ids = get_document_qdrant_point_ids(document_id=document_id)
    delete_vectors_by_point_ids(point_ids=qdrant_point_ids)

    deleted = delete_document_by_id(document_id=document_id)

    if not deleted:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document from PostgreSQL.",
        )

    return {
        "document_id": document_id,
        "deleted_qdrant_point_count": len(qdrant_point_ids),
        "message": "Admin content deleted successfully.",
    }


@app.post("/search", response_model=list[SearchResult])
def search_documents(search_request: SearchRequest):
    """
    Search stored document/chunk vectors in Qdrant.

    Optional filters:
    - subject
    - topic
    - subtopic
    - difficulty
    - lang
    - tags
    """
    return search_document_vectors(
        query=search_request.query,
        limit=search_request.limit,
        subject=search_request.subject,
        topic=search_request.topic,
        subtopic=search_request.subtopic,
        difficulty=search_request.difficulty,
        lang=search_request.lang,
        tags=search_request.tags,
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(ask_request: AskRequest):
    """
    RAG endpoint using DeepSeek for answer generation.

    Flow:
    - retrieve relevant documents/chunks from Qdrant
    - optional metadata filters narrow retrieved content
    - combine retrieved content as context
    - send question + context to DeepSeek
    - log the ask event in PostgreSQL
    - return generated answer with sources
    """
    sources = search_document_vectors(
        query=ask_request.question,
        limit=ask_request.limit,
        subject=ask_request.subject,
        topic=ask_request.topic,
        subtopic=ask_request.subtopic,
        difficulty=ask_request.difficulty,
        lang=ask_request.lang,
        tags=ask_request.tags,
    )

    if not sources:
        fallback_answer = "I could not find any relevant documents."

        insert_event_log(
            event_type="rag_ask_no_sources",
            question=ask_request.question,
            answer=fallback_answer,
            subject=ask_request.subject,
            topic=ask_request.topic,
            subtopic=ask_request.subtopic,
            difficulty=ask_request.difficulty,
            lang=ask_request.lang,
            tags=ask_request.tags,
            source_count=0,
            source_chunk_ids=[],
            metadata={
                "limit": ask_request.limit,
            },
        )

        return {
            "question": ask_request.question,
            "answer": fallback_answer,
            "sources": [],
        }

    context_parts = []

    for index, source in enumerate(sources, start=1):
        context_parts.append(
            f"Source {index}\n"
            f"Title: {source['title']}\n"
            f"Content: {source['content']}\n"
            f"Source: {source.get('source')}\n"
            f"Subject: {source.get('subject')}\n"
            f"Topic: {source.get('topic')}\n"
            f"Subtopic: {source.get('subtopic')}\n"
            f"Page: {source.get('page')}\n"
            f"Chunk ID: {source.get('chunk_id')}\n"
        )

    context = "\n---\n".join(context_parts)

    answer = generate_answer(
        question=ask_request.question,
        context=context,
    )

    source_chunk_ids = [
        source.get("chunk_id")
        for source in sources
        if source.get("chunk_id")
    ]

    insert_event_log(
        event_type="rag_ask",
        question=ask_request.question,
        answer=answer,
        subject=ask_request.subject,
        topic=ask_request.topic,
        subtopic=ask_request.subtopic,
        difficulty=ask_request.difficulty,
        lang=ask_request.lang,
        tags=ask_request.tags,
        source_count=len(sources),
        source_chunk_ids=source_chunk_ids,
        metadata={
            "limit": ask_request.limit,
            "source_titles": [source.get("title") for source in sources],
            "source_scores": [source.get("score") for source in sources],
        },
    )

    return {
        "question": ask_request.question,
        "answer": answer,
        "sources": sources,
    }
    

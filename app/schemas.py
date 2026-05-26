from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str
    content: str
    source: str | None = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    source: str | None = None
    qdrant_point_id: str | None = None


class TextIngestRequest(BaseModel):
    """
    Request body for ingesting course content into the RAG pipeline.

    Metadata follows the Buddy AI task-guide structure:
    - subject: high-level course subject
    - topic: lesson/topic name
    - subtopic: smaller section inside the topic
    - difficulty: numeric level, usually 1-5
    - lang: language code, for example "en"
    - source: file name, URL, Google Drive source, etc.
    - page: page number if content came from a PDF/document
    - tags: searchable tags
    """

    title: str
    content: str
    source: str | None = None

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    lang: str | None = "en"
    page: int | None = None
    tags: list[str] = Field(default_factory=list)


class TextIngestResponse(BaseModel):
    document_id: int
    title: str
    source: str | None = None
    chunk_count: int
    qdrant_point_ids: list[str]


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    lang: str | None = None
    tags: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    title: str
    content: str
    source: str | None = None
    score: float

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = None
    lang: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    limit: int = Field(default=3, ge=1, le=10)

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    lang: str | None = None
    tags: list[str] = Field(default_factory=list)


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SearchResult]


class AdminContentCreate(BaseModel):
    """
    Admin request body for adding learning content.

    This uses the same RAG ingestion structure as /ingest/text,
    but it is placed under /admin/content for frontend admin workflows.
    """

    title: str
    content: str
    source: str | None = None

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    lang: str | None = "en"
    page: int | None = None
    tags: list[str] = Field(default_factory=list)


class AdminContentUpdate(BaseModel):
    """
    Admin request body for editing learning content.

    All fields are optional so the frontend can update only what changed.
    If content or metadata changes, the backend will rebuild document chunks
    and replace the matching Qdrant vectors.
    """

    title: str | None = None
    content: str | None = None
    source: str | None = None

    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    lang: str | None = None
    page: int | None = None
    tags: list[str] | None = None


class AdminContentSummary(BaseModel):
    id: int
    title: str
    source: str | None = None
    chunk_count: int
    created_at: str | None = None


class AdminContentDetail(BaseModel):
    id: int
    title: str
    content: str
    source: str | None = None
    qdrant_point_id: str | None = None
    chunk_count: int
    chunks: list[dict]
    created_at: str | None = None


class AdminContentMutationResponse(BaseModel):
    document_id: int
    title: str
    source: str | None = None
    chunk_count: int
    qdrant_point_ids: list[str]
    message: str

    
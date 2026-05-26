import json

import psycopg

from app.config import settings


def get_connection():
    """
    Create a PostgreSQL connection.

    Priority:
    1. DATABASE_URL from .env for Supabase or hosted PostgreSQL.
    2. Local Docker PostgreSQL values from POSTGRES_* variables.

    Supabase note:
    Use the Supabase PostgreSQL connection string as DATABASE_URL.
    Do not commit DATABASE_URL to GitHub.
    """
    if settings.database_url:
        return psycopg.connect(settings.database_url)

    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def check_database_connection() -> bool:
    """
    Simple health check for PostgreSQL.
    Returns True if the database responds.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()
                return result[0] == 1
    except Exception as error:
        print(f"Database connection failed: {error}")
        return False


def insert_document(
    title: str,
    content: str,
    source: str | None = None,
    qdrant_point_id: str | None = None,
) -> dict:
    """
    Insert a document into PostgreSQL and return the saved row.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (title, content, source, qdrant_point_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, content, source, qdrant_point_id;
                """,
                (title, content, source, qdrant_point_id),
            )
            row = cur.fetchone()
            conn.commit()

    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "source": row[3],
        "qdrant_point_id": row[4],
    }


def insert_document_chunk(
    document_id: int,
    chunk_index: int,
    chunk_id: str,
    content: str,
    source: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    difficulty: int | None = None,
    lang: str | None = "en",
    page: int | None = None,
    tags: list[str] | None = None,
    qdrant_point_id: str | None = None,
) -> dict:
    """
    Insert one document chunk into PostgreSQL and return the saved row.
    """
    safe_tags = tags or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_chunks (
                    document_id,
                    chunk_index,
                    chunk_id,
                    content,
                    source,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    page,
                    tags,
                    qdrant_point_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    document_id,
                    chunk_index,
                    chunk_id,
                    content,
                    source,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    page,
                    tags,
                    qdrant_point_id;
                """,
                (
                    document_id,
                    chunk_index,
                    chunk_id,
                    content,
                    source,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    page,
                    safe_tags,
                    qdrant_point_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()

    return {
        "id": row[0],
        "document_id": row[1],
        "chunk_index": row[2],
        "chunk_id": row[3],
        "content": row[4],
        "source": row[5],
        "subject": row[6],
        "topic": row[7],
        "subtopic": row[8],
        "difficulty": row[9],
        "lang": row[10],
        "page": row[11],
        "tags": row[12],
        "qdrant_point_id": row[13],
    }


def insert_event_log(
    event_type: str,
    question: str | None = None,
    answer: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    subtopic: str | None = None,
    difficulty: int | None = None,
    lang: str | None = None,
    tags: list[str] | None = None,
    source_count: int = 0,
    source_chunk_ids: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Insert one backend activity event into PostgreSQL.
    """
    safe_tags = tags or []
    safe_source_chunk_ids = source_chunk_ids or []
    safe_metadata = metadata or {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (
                    event_type,
                    question,
                    answer,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    tags,
                    source_count,
                    source_chunk_ids,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING
                    id,
                    event_type,
                    question,
                    source_count,
                    source_chunk_ids,
                    created_at;
                """,
                (
                    event_type,
                    question,
                    answer,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    safe_tags,
                    source_count,
                    safe_source_chunk_ids,
                    json.dumps(safe_metadata),
                ),
            )
            row = cur.fetchone()
            conn.commit()

    return {
        "id": row[0],
        "event_type": row[1],
        "question": row[2],
        "source_count": row[3],
        "source_chunk_ids": row[4],
        "created_at": row[5],
    }


def get_recent_events(limit: int = 10) -> list[dict]:
    """
    Read recent backend activity events from PostgreSQL.
    """
    safe_limit = max(1, min(limit, 50))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    event_type,
                    question,
                    answer,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    tags,
                    source_count,
                    source_chunk_ids,
                    metadata,
                    created_at
                FROM events
                ORDER BY id DESC
                LIMIT %s;
                """,
                (safe_limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "event_type": row[1],
            "question": row[2],
            "answer": row[3],
            "subject": row[4],
            "topic": row[5],
            "subtopic": row[6],
            "difficulty": row[7],
            "lang": row[8],
            "tags": row[9],
            "source_count": row[10],
            "source_chunk_ids": row[11],
            "metadata": row[12],
            "created_at": row[13],
        }
        for row in rows
    ]


def get_progress_summary() -> dict:
    """
    Build a simple learning progress summary from the events table.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_questions,
                    COUNT(DISTINCT subject) FILTER (WHERE subject IS NOT NULL) AS subject_count,
                    COUNT(DISTINCT topic) FILTER (WHERE topic IS NOT NULL) AS topic_count,
                    COUNT(DISTINCT subtopic) FILTER (WHERE subtopic IS NOT NULL) AS subtopic_count,
                    COALESCE(ROUND(AVG(source_count)::numeric, 2), 0) AS average_source_count,
                    MAX(created_at) AS latest_activity
                FROM events
                WHERE event_type IN ('rag_ask', 'rag_ask_no_sources');
                """
            )
            summary_row = cur.fetchone()

            cur.execute(
                """
                SELECT DISTINCT subject
                FROM events
                WHERE subject IS NOT NULL
                ORDER BY subject;
                """
            )
            subject_rows = cur.fetchall()

            cur.execute(
                """
                SELECT DISTINCT topic
                FROM events
                WHERE topic IS NOT NULL
                ORDER BY topic;
                """
            )
            topic_rows = cur.fetchall()

            cur.execute(
                """
                SELECT DISTINCT subtopic
                FROM events
                WHERE subtopic IS NOT NULL
                ORDER BY subtopic;
                """
            )
            subtopic_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    subject,
                    topic,
                    subtopic,
                    COUNT(*) AS question_count,
                    COALESCE(ROUND(AVG(source_count)::numeric, 2), 0) AS average_source_count,
                    MAX(created_at) AS latest_activity
                FROM events
                WHERE event_type IN ('rag_ask', 'rag_ask_no_sources')
                GROUP BY subject, topic, subtopic
                ORDER BY question_count DESC, latest_activity DESC
                LIMIT 10;
                """
            )
            focus_rows = cur.fetchall()

    return {
        "total_questions": summary_row[0],
        "subject_count": summary_row[1],
        "topic_count": summary_row[2],
        "subtopic_count": summary_row[3],
        "average_source_count": float(summary_row[4]),
        "latest_activity": summary_row[5],
        "subjects_practiced": [row[0] for row in subject_rows],
        "topics_practiced": [row[0] for row in topic_rows],
        "subtopics_practiced": [row[0] for row in subtopic_rows],
        "top_focus_areas": [
            {
                "subject": row[0],
                "topic": row[1],
                "subtopic": row[2],
                "question_count": row[3],
                "average_source_count": float(row[4]),
                "latest_activity": row[5],
            }
            for row in focus_rows
        ],
    }


def get_progress_by_subject() -> list[dict]:
    """
    Build detailed progress grouped by subject, topic, and subtopic.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    subject,
                    topic,
                    subtopic,
                    COUNT(*) AS question_count,
                    COUNT(*) FILTER (WHERE event_type = 'rag_ask') AS answered_count,
                    COUNT(*) FILTER (WHERE event_type = 'rag_ask_no_sources') AS no_source_count,
                    COALESCE(ROUND(AVG(source_count)::numeric, 2), 0) AS average_source_count,
                    MIN(created_at) AS first_activity,
                    MAX(created_at) AS latest_activity
                FROM events
                WHERE event_type IN ('rag_ask', 'rag_ask_no_sources')
                GROUP BY subject, topic, subtopic
                ORDER BY subject, topic, subtopic;
                """
            )
            rows = cur.fetchall()

    return [
        {
            "subject": row[0],
            "topic": row[1],
            "subtopic": row[2],
            "question_count": row[3],
            "answered_count": row[4],
            "no_source_count": row[5],
            "average_source_count": float(row[6]),
            "first_activity": row[7],
            "latest_activity": row[8],
        }
        for row in rows
    ]


def get_recent_questions(limit: int = 10) -> list[dict]:
    """
    Read recent student questions in a clean progress-friendly format.
    """
    safe_limit = max(1, min(limit, 50))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    question,
                    answer,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    tags,
                    source_count,
                    created_at
                FROM events
                WHERE event_type IN ('rag_ask', 'rag_ask_no_sources')
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (safe_limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "question": row[0],
            "answer": row[1],
            "subject": row[2],
            "topic": row[3],
            "subtopic": row[4],
            "difficulty": row[5],
            "lang": row[6],
            "tags": row[7],
            "source_count": row[8],
            "created_at": row[9],
        }
        for row in rows
    ]


def get_weak_areas() -> list[dict]:
    """
    Detect weak retrieval areas from RAG activity.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    subject,
                    topic,
                    subtopic,
                    COUNT(*) AS failed_question_count,
                    MAX(question) AS latest_failed_question,
                    MAX(created_at) AS latest_activity
                FROM events
                WHERE event_type = 'rag_ask_no_sources'
                OR source_count = 0
                GROUP BY subject, topic, subtopic
                ORDER BY failed_question_count DESC, latest_activity DESC;
                """
            )
            rows = cur.fetchall()

    return [
        {
            "subject": row[0],
            "topic": row[1],
            "subtopic": row[2],
            "failed_question_count": row[3],
            "latest_failed_question": row[4],
            "latest_activity": row[5],
        }
        for row in rows
    ]


def get_progress_recommendations() -> list[dict]:
    """
    Generate simple study recommendations using existing progress data.

    Recommendation priority:
    1. Weak areas from no-source RAG events
    2. Recent student activity
    3. Starter recommendation if no activity exists
    """
    weak_areas = get_weak_areas()
    recent_questions = get_recent_questions(limit=5)

    recommendations = []

    for weak_area in weak_areas:
        subject = weak_area.get("subject") or "General"
        topic = weak_area.get("topic") or "Unknown Topic"
        subtopic = weak_area.get("subtopic") or "Unknown Subtopic"

        recommendations.append(
            {
                "type": "weak_area",
                "priority": "high",
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
                "reason": "The student asked questions in this area, but the system could not find enough matching learning content.",
                "recommended_action": f"Review this area or add more learning content for {subject} / {topic} / {subtopic}.",
                "source": "progress_weak_areas",
            }
        )

    if not recommendations and recent_questions:
        latest_question = recent_questions[0]

        recommendations.append(
            {
                "type": "recent_activity",
                "priority": "medium",
                "subject": latest_question.get("subject") or "General",
                "topic": latest_question.get("topic") or "Recent Topic",
                "subtopic": latest_question.get("subtopic") or "Recent Subtopic",
                "reason": "No weak areas were detected, so the recommendation is based on the student's latest activity.",
                "recommended_action": "Continue practicing this topic and ask follow-up questions to strengthen understanding.",
                "source": "progress_recent_questions",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "type": "starter",
                "priority": "low",
                "subject": "General",
                "topic": "Getting Started",
                "subtopic": "First Practice",
                "reason": "No student activity has been recorded yet.",
                "recommended_action": "Ingest learning content and ask a first question to generate personalized recommendations.",
                "source": "default",
            }
        )

    return recommendations


def get_progress_dashboard() -> dict:
    """
    Build a combined student progress dashboard.

    This is useful for frontend/n8n because it returns the main progress data
    in one response instead of calling multiple endpoints separately.
    """
    return {
        "summary": get_progress_summary(),
        "by_subject": get_progress_by_subject(),
        "recent_questions": get_recent_questions(limit=5),
        "weak_areas": get_weak_areas(),
        "recommendations": get_progress_recommendations(),
    }


def get_admin_content_list(limit: int = 20, offset: int = 0) -> list[dict]:
    """
    List learning content for admin dashboard.

    Returns one row per document with chunk count.
    """
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    documents.id,
                    documents.title,
                    documents.source,
                    COUNT(document_chunks.id) AS chunk_count,
                    documents.created_at
                FROM documents
                LEFT JOIN document_chunks
                    ON document_chunks.document_id = documents.id
                GROUP BY documents.id
                ORDER BY documents.id DESC
                LIMIT %s OFFSET %s;
                """,
                (safe_limit, safe_offset),
            )
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "source": row[2],
            "chunk_count": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


def get_admin_content_detail(document_id: int) -> dict | None:
    """
    Read one document and its chunks for admin view/edit screen.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    title,
                    content,
                    source,
                    qdrant_point_id,
                    created_at
                FROM documents
                WHERE id = %s;
                """,
                (document_id,),
            )
            document_row = cur.fetchone()

            if not document_row:
                return None

            cur.execute(
                """
                SELECT
                    id,
                    document_id,
                    chunk_index,
                    chunk_id,
                    content,
                    source,
                    subject,
                    topic,
                    subtopic,
                    difficulty,
                    lang,
                    page,
                    tags,
                    qdrant_point_id,
                    created_at
                FROM document_chunks
                WHERE document_id = %s
                ORDER BY chunk_index ASC;
                """,
                (document_id,),
            )
            chunk_rows = cur.fetchall()

    chunks = [
        {
            "id": row[0],
            "document_id": row[1],
            "chunk_index": row[2],
            "chunk_id": row[3],
            "content": row[4],
            "source": row[5],
            "subject": row[6],
            "topic": row[7],
            "subtopic": row[8],
            "difficulty": row[9],
            "lang": row[10],
            "page": row[11],
            "tags": row[12],
            "qdrant_point_id": row[13],
            "created_at": row[14].isoformat() if row[14] else None,
        }
        for row in chunk_rows
    ]

    return {
        "id": document_row[0],
        "title": document_row[1],
        "content": document_row[2],
        "source": document_row[3],
        "qdrant_point_id": document_row[4],
        "chunk_count": len(chunks),
        "chunks": chunks,
        "created_at": document_row[5].isoformat() if document_row[5] else None,
    }


def get_document_qdrant_point_ids(document_id: int) -> list[str]:
    """
    Get all Qdrant point IDs connected to a document.

    Includes:
    - document-level qdrant_point_id from documents table
    - chunk-level qdrant_point_id values from document_chunks table
    """
    point_ids = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT qdrant_point_id
                FROM documents
                WHERE id = %s
                AND qdrant_point_id IS NOT NULL;
                """,
                (document_id,),
            )
            document_rows = cur.fetchall()

            cur.execute(
                """
                SELECT qdrant_point_id
                FROM document_chunks
                WHERE document_id = %s
                AND qdrant_point_id IS NOT NULL;
                """,
                (document_id,),
            )
            chunk_rows = cur.fetchall()

    for row in document_rows + chunk_rows:
        if row[0]:
            point_ids.append(row[0])

    return point_ids


def update_document_base(
    document_id: int,
    title: str,
    content: str,
    source: str | None = None,
    qdrant_point_id: str | None = None,
) -> dict | None:
    """
    Update the main document row after admin edit.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET
                    title = %s,
                    content = %s,
                    source = %s,
                    qdrant_point_id = %s
                WHERE id = %s
                RETURNING id, title, content, source, qdrant_point_id;
                """,
                (title, content, source, qdrant_point_id, document_id),
            )
            row = cur.fetchone()
            conn.commit()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "source": row[3],
        "qdrant_point_id": row[4],
    }


def delete_document_chunks(document_id: int) -> int:
    """
    Delete PostgreSQL chunk rows for one document.
    Returns number of deleted chunk rows.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s;
                """,
                (document_id,),
            )
            deleted_count = cur.rowcount
            conn.commit()

    return deleted_count


def delete_document_by_id(document_id: int) -> bool:
    """
    Delete one document from PostgreSQL.

    document_chunks has ON DELETE CASCADE, but we still delete Qdrant vectors
    from the API layer before calling this function.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s;
                """,
                (document_id,),
            )
            deleted = cur.rowcount > 0
            conn.commit()

    return deleted

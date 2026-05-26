from app.db import get_connection


def create_tables() -> None:
    """
    Create and migrate database tables required by the Buddy AI backend.

    documents:
    - stores original ingested documents/text

    document_chunks:
    - stores chunked course content
    - links each chunk to a parent document
    - stores metadata used for RAG filtering and source tracing
    - qdrant_point_id links each row to the vector stored in Qdrant

    events:
    - stores backend activity logs
    - tracks RAG ask events, filters used, and retrieved source chunks
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    qdrant_point_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    chunk_id TEXT UNIQUE,
                    content TEXT NOT NULL,

                    source TEXT,
                    subject TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    difficulty INTEGER,
                    lang TEXT DEFAULT 'en',
                    page INTEGER,
                    tags TEXT[] DEFAULT '{}',

                    qdrant_point_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    question TEXT,
                    answer TEXT,

                    subject TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    difficulty INTEGER,
                    lang TEXT,
                    tags TEXT[] DEFAULT '{}',

                    source_count INTEGER DEFAULT 0,
                    source_chunk_ids TEXT[] DEFAULT '{}',

                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            migrate_document_chunks_table(cur)
            migrate_events_table(cur)

            conn.commit()


def migrate_document_chunks_table(cur) -> None:
    """
    Upgrade older local document_chunks tables to the current metadata schema.

    Current schema:
    - chunk_id TEXT
    - subtopic TEXT
    - difficulty INTEGER from 1 to 5
    - lang TEXT
    - tags TEXT[]

    Difficulty mapping:
    - beginner/basic/easy -> 1
    - intermediate/medium -> 3
    - advanced/hard -> 5
    - valid numeric strings 1-5 stay unchanged
    - invalid values become NULL
    """

    cur.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS chunk_id TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS subtopic TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'en';
        """
    )

    cur.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'document_chunks'
                AND column_name = 'language'
            ) THEN
                EXECUTE 'UPDATE document_chunks SET lang = language WHERE lang IS NULL';
            END IF;
        END $$;
        """
    )

    cur.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'document_chunks'
                AND column_name = 'difficulty'
                AND data_type <> 'integer'
            ) THEN
                EXECUTE '
                    UPDATE document_chunks
                    SET difficulty = CASE
                        WHEN difficulty IS NULL OR trim(difficulty::text) = '''' THEN NULL
                        WHEN lower(trim(difficulty::text)) IN (''beginner'', ''basic'', ''easy'') THEN ''1''
                        WHEN lower(trim(difficulty::text)) IN (''intermediate'', ''medium'') THEN ''3''
                        WHEN lower(trim(difficulty::text)) IN (''advanced'', ''hard'') THEN ''5''
                        WHEN trim(difficulty::text) ~ ''^[1-5]$'' THEN trim(difficulty::text)
                        ELSE NULL
                    END
                    WHERE difficulty IS NOT NULL
                ';

                EXECUTE '
                    ALTER TABLE document_chunks
                    ALTER COLUMN difficulty TYPE INTEGER
                    USING difficulty::integer
                ';
            END IF;
        END $$;
        """
    )

    cur.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'document_chunks'
                AND column_name = 'tags'
                AND data_type <> 'ARRAY'
            ) THEN
                ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tags_array TEXT[] DEFAULT '{}';

                EXECUTE '
                    UPDATE document_chunks
                    SET tags_array = CASE
                        WHEN tags IS NULL OR tags = '''' THEN ''{}''::TEXT[]
                        ELSE ARRAY[tags]
                    END
                ';

                ALTER TABLE document_chunks DROP COLUMN tags;
                ALTER TABLE document_chunks RENAME COLUMN tags_array TO tags;
            END IF;
        END $$;
        """
    )

    cur.execute(
        """
        UPDATE document_chunks
        SET chunk_id = qdrant_point_id
        WHERE chunk_id IS NULL
        AND qdrant_point_id IS NOT NULL;
        """
    )


def migrate_events_table(cur) -> None:
    """
    Upgrade older local events tables to the current progress/recommendation schema.

    This prevents startup/runtime crashes when the events table already exists
    but does not have the latest columns.
    """

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS question TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS answer TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS subject TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS topic TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS subtopic TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS difficulty INTEGER;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS lang TEXT;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS source_count INTEGER DEFAULT 0;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS source_chunk_ids TEXT[] DEFAULT '{}';
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
        """
    )

    cur.execute(
        """
        ALTER TABLE events
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """
    )
    
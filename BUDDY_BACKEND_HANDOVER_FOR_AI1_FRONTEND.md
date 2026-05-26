# Buddy Backend Handover Guide for AI Engineer 1 and Frontend
Owner:
Tharuka - AI Engineer 2
Backend repo:
buddy-ai-backend-rag
---
## Purpose
This document explains how AI Engineer 1, n8n workflows, and frontend screens should integrate with the Buddy backend.
The backend provides:
- RAG ingestion
- file upload ingestion
- Qdrant semantic search
- OpenAI answer generation
- PostgreSQL/Supabase metadata storage
- progress tracking
- admin content management APIs
---
## Current Backend Architecture
Current recommended architecture:
    Frontend / n8n
        ?
    FastAPI backend
        ?
    OpenAI embeddings
        ?
    Qdrant course_content collection
        ?
    OpenAI answer generation
        ?
    PostgreSQL / Supabase for documents, chunks, events, and progress
---
## Main Services
FastAPI backend:
    http://localhost:8000
Swagger UI:
    http://localhost:8000/docs
Qdrant dashboard:
    http://localhost:6333/dashboard
n8n:
    http://localhost:5678
Database:
    Local development: Docker PostgreSQL
    Shared team DB: Supabase PostgreSQL through DATABASE_URL
---
## Environment Variables Needed
The backend uses `.env`.
Important values:
    APP_NAME=Buddy AI Backend
    APP_ENV=local
    QDRANT_HOST=localhost
    QDRANT_PORT=6333
    QDRANT_COLLECTION=course_content
    OPENAI_API_KEY=your_openai_key_here
    OPENAI_EMBEDDING_MODEL=text-embedding-3-small
    EMBEDDING_PROVIDER=openai
    LLM_PROVIDER=openai
    OPENAI_CHAT_MODEL=gpt-4o-mini
Optional DeepSeek fallback:
    DEEPSEEK_API_KEY=your_deepseek_key_here
    DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
    DEEPSEEK_MODEL=deepseek-chat
For Supabase shared database:
    DATABASE_URL=your_supabase_postgres_connection_string_here
Important:
Do not commit real API keys or real DATABASE_URL values to GitHub.
---
## Supabase Database Plan
The backend already supports Supabase through:
    DATABASE_URL
Connection behavior:
    If DATABASE_URL exists:
        backend uses Supabase / hosted PostgreSQL
    If DATABASE_URL is empty:
        backend uses local Docker PostgreSQL settings
Required tables are created/migrated automatically on backend startup:
- documents
- document_chunks
- events
Supabase is used for relational data:
- documents
- chunks
- metadata
- event logs
- progress data
Qdrant is still used for vector search.
Important:
Supabase does not replace Qdrant in the current architecture.
---
## Qdrant Role
Qdrant stores vectors for RAG retrieval.
Collection:
    course_content
Vector setup:
- size: 768
- distance: Cosine
- embeddings: OpenAI text-embedding-3-small
Qdrant payload metadata includes:
- subject
- topic
- subtopic
- difficulty
- lang
- source
- page
- chunk_id
- tags
---
## Answer Generation
Current provider:
    LLM_PROVIDER=openai
Current chat model:
    OPENAI_CHAT_MODEL=gpt-4o-mini
DeepSeek fallback remains available:
    LLM_PROVIDER=deepseek
The frontend and n8n do not need to know which LLM is used internally. They only call:
    POST /ask
---
## Endpoints for Frontend
### Health
    GET /health
Use this to check backend status.
---
### Ask Buddy
    POST /ask
Use this when the student asks a question and needs a final generated answer.
Example JSON:
    {
      "question": "What parts of the robot does the battery power?",
      "limit": 3,
      "subject": "robotics",
      "topic": "power",
      "subtopic": "battery voltage and capacity",
      "difficulty": 2,
      "lang": "en",
      "tags": ["pdf"]
    }
Returns:
- question
- answer
- sources
Frontend should show:
- answer
- source title
- source content snippet
- source metadata if needed
---
### Search Only
    POST /search
Use this when frontend or n8n needs retrieved source chunks but not a generated answer.
Example JSON:
    {
      "query": "what does a sensor do?",
      "limit": 3,
      "subject": "robotics",
      "topic": "sensors",
      "difficulty": 1,
      "lang": "en",
      "tags": ["sensor"]
    }
Returns matching chunks from Qdrant.
---
### Progress Dashboard
    GET /progress/me
Use this for the student dashboard.
Returns:
- summary
- by_subject
- recent_questions
- weak_areas
- recommendations
This is the recommended frontend endpoint for progress screens because it combines the important progress data into one response.
---
## Endpoints for Admin Frontend
Admin endpoints require this header:
    X-User-Role: admin
This is local/demo auth. Production should use real JWT/session auth.
---
### Admin Content List
    GET /admin/content?limit=5&offset=0
Header:
    X-User-Role: admin
Use this to show all uploaded/ingested learning content.
---
### Admin Content Detail
    GET /admin/content/{document_id}
Header:
    X-User-Role: admin
Use this to view one document and its chunks.
---
### Admin Create Text Content
    POST /admin/content
Header:
    X-User-Role: admin
Use this when admin manually adds text content.
---
### Admin Update Content
    PATCH /admin/content/{document_id}
Header:
    X-User-Role: admin
Use this when admin edits learning content.
Important:
Update deletes old Qdrant vectors and old chunks, then re-chunks and re-indexes the updated content.
---
### Admin Delete Content
    DELETE /admin/content/{document_id}
Header:
    X-User-Role: admin
Use this when admin deletes learning content.
Important:
Delete removes both PostgreSQL/Supabase data and Qdrant vectors.
---
## File Upload for Frontend
Endpoint:
    POST /ingest/file
Use multipart/form-data.
Supported files:
- .txt
- .md
- .pdf
- .docx
Form fields:
- file: required
- title: optional
- source: optional
- subject: optional
- topic: optional
- subtopic: optional
- difficulty: optional, 1 to 5
- lang: optional, default en
- page: optional
- tags: optional comma-separated string
Example curl:
    curl.exe -X POST "http://localhost:8000/ingest/file" -F "file=@lesson.pdf" -F "title=Lesson PDF" -F "subject=robotics" -F "topic=power" -F "subtopic=battery voltage and capacity" -F "difficulty=2" -F "lang=en" -F "tags=robotics,battery,pdf"
Successful response:
    {
      "document_id": 16,
      "title": "Lesson PDF",
      "source": "lesson.pdf",
      "chunk_count": 1,
      "qdrant_point_ids": ["..."]
    }
Unsupported file response:
    {
      "detail": "Unsupported file type '.csv'. Supported types: .docx, .md, .pdf, .txt"
    }
---
## Endpoints for AI Engineer 1 / n8n
Recommended n8n workflow calls:
1. Student asks question:
       POST /ask
2. Need only retrieval:
       POST /search
3. Need progress dashboard:
       GET /progress/me
4. Need weak areas:
       GET /progress/weak-areas
5. Need recommendations:
       GET /progress/recommendations
6. Admin uploads/updates content:
       POST /ingest/file
       POST /admin/content
       PATCH /admin/content/{document_id}
       DELETE /admin/content/{document_id}
---
## Important Notes for AI Engineer 1
The n8n layer should not directly connect to Qdrant for normal user questions.
Recommended flow:
    n8n receives user question
        ?
    n8n calls backend POST /ask
        ?
    backend handles retrieval and answer generation
        ?
    n8n formats/sends response
This keeps RAG logic centralized in the backend.
---
## Important Notes for Frontend
Frontend should not call Qdrant directly.
Frontend should call FastAPI only.
Recommended frontend screens:
Student chat:
    POST /ask
Student progress dashboard:
    GET /progress/me
Admin content list:
    GET /admin/content
Admin content upload:
    POST /ingest/file
Admin content detail/edit/delete:
    GET /admin/content/{document_id}
    PATCH /admin/content/{document_id}
    DELETE /admin/content/{document_id}
---
## Current Proven Features
Completed and tested:
- FastAPI backend health
- PostgreSQL local DB
- Supabase-ready DATABASE_URL support
- Qdrant vector storage
- OpenAI embeddings
- OpenAI answer generation
- DeepSeek fallback
- text ingestion
- file upload ingestion
- TXT upload
- DOCX upload
- PDF upload
- unsupported CSV rejection
- semantic search
- RAG ask
- event logging
- progress dashboard
- weak areas
- recommendations
- admin content list/detail/create/update/delete
- admin route protection
---
## Current Limitations
- Supabase needs a real project connection string before shared DB testing.
- Qdrant still runs separately from Supabase.
- PDF extraction supports text-based PDFs only.
- Scanned PDFs require OCR, which is not included yet.
- Admin auth is demo-level using X-User-Role: admin.
- Production should use JWT/session auth.
- Sinhala quality should be tested with real Sinhala lesson content and questions.
---
## Recommended Integration Order
1. Frontend connects to `/health`.
2. Frontend tests `/ask`.
3. Frontend tests `/progress/me`.
4. Admin frontend tests `/admin/content`.
5. Admin frontend tests `/ingest/file`.
6. AI Engineer 1 connects n8n to `/ask`.
7. Team sets shared Supabase `DATABASE_URL`.
8. Backend is restarted and `/health` is tested.
9. One test content item is inserted and verified in Supabase.
---


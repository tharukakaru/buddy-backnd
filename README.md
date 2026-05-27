# Buddy AI Backend - RAG Foundation
This project is the local backend foundation for Buddy AI.
It includes:
- FastAPI backend APIs
- PostgreSQL metadata storage
- Qdrant vector database integration
- OpenAI embedding support
- provider-based answer generation with OpenAI as current provider and DeepSeek fallback
- RAG document ingestion
- File upload ingestion
- Semantic search
- RAG ask endpoint
- Progress tracking APIs
- Admin content management APIs
---
## Owner
Tharuka - AI Engineer 2
---
## Responsibilities Covered
- Backend API setup using FastAPI
- PostgreSQL database setup
- Qdrant vector database setup
- RAG text ingestion
- File upload ingestion for TXT, MD, PDF, and DOCX
- Long text chunking
- Chunk metadata storage
- 768-dimensional OpenAI embeddings
- Semantic search
- RAG ask endpoint using retrieved context and provider-based answer generation with OpenAI as current provider and DeepSeek fallback
- Backend event logging
- Progress tracking endpoints
- Progress recommendation endpoint
- Admin content management APIs
- Demo-level admin route protection
---
## Tech Stack
- Python
- FastAPI
- PostgreSQL
- Qdrant
- Docker
- Docker Compose
- n8n
- OpenAI embeddings
- DeepSeek
- pypdf
- python-docx
- python-multipart
---
## Local Services
| Service | URL | Purpose |
|---|---|---|
| FastAPI Backend | http://127.0.0.1:8000 | Backend API |
| Swagger Docs | http://127.0.0.1:8000/docs | API testing |
| Qdrant Dashboard | http://localhost:6333/dashboard | Vector DB dashboard |
| n8n | http://localhost:5678 | Workflow automation |
| PostgreSQL | localhost:5432 | Document, chunk, and event metadata DB |
---
## Main Local Commands
Start Docker services:
    docker compose up -d
Start backend:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Check backend health:
    curl.exe http://localhost:8000/health
Check Qdrant health:
    curl.exe http://localhost:6333/healthz
---
## Environment Configuration
The backend uses `.env`.
Important values:
    QDRANT_HOST=localhost
    QDRANT_PORT=6333
    QDRANT_COLLECTION=course_content
    OPENAI_EMBEDDING_MODEL=text-embedding-3-small
    EMBEDDING_PROVIDER=openai
    DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
    DEEPSEEK_MODEL=deepseek-chat

## Qdrant Configuration
Main collection:
    course_content
Confirmed configuration:
- Vector size: 768
- Distance: Cosine
- HNSW m=16
- HNSW ef_construct=128
- Sparse vector support with BM25-style config
---
## API Endpoints
### General Backend
    GET /
    GET /health
### Document and RAG
    POST /documents
    POST /ingest/text
    POST /ingest/file
    POST /search
    POST /ask
### Progress
    GET /events/recent
    GET /progress/summary
    GET /progress/by-subject
    GET /progress/recent-questions
    GET /progress/weak-areas
    GET /progress/recommendations
    GET /progress/me
### Admin Content
    GET /admin/content
    GET /admin/content/{document_id}
    POST /admin/content
    PATCH /admin/content/{document_id}
    DELETE /admin/content/{document_id}
---
## Health Check
Endpoint:
    GET /health
Example:
    curl.exe http://localhost:8000/health
Expected response:
    {
      "status": "ok",
      "services": {
        "postgres": true,
        "qdrant": true
      }
    }
---
## Text Ingestion
Endpoint:
    POST /ingest/text
Use this when the client already has raw text content.
Example JSON:
    {
      "title": "Robotics Sensor Lesson",
      "content": "A robot sensor detects the environment and sends signals to the controller.",
      "source": "manual-entry",
      "subject": "robotics",
      "topic": "sensors",
      "subtopic": "environment sensing",
      "difficulty": 1,
      "lang": "en",
      "page": 1,
      "tags": ["robotics", "sensor"]
    }
What it does:
1. Saves the original document in PostgreSQL.
2. Splits text into chunks.
3. Stores chunk vectors in Qdrant.
4. Stores chunk metadata in PostgreSQL.
5. Returns document ID, chunk count, and Qdrant point IDs.
---
## File Upload Ingestion
Endpoint:
    POST /ingest/file
Supported file types:
- TXT
- MD
- PDF
- DOCX
Example:
    curl.exe -X POST "http://localhost:8000/ingest/file" -F "file=@robotics-battery-test.pdf" -F "title=Robotics Battery PDF Test" -F "source=robotics-battery-test.pdf" -F "subject=robotics" -F "topic=power" -F "subtopic=battery voltage and capacity" -F "difficulty=2" -F "lang=en" -F "tags=robotics,battery,pdf"
Confirmed file upload tests:
- TXT upload
- DOCX upload
- PDF upload
- unsupported CSV rejection
Unsupported file example response:
    {
      "detail": "Unsupported file type '.csv'. Supported types: .docx, .md, .pdf, .txt"
    }
---
## Semantic Search
Endpoint:
    POST /search
Purpose:
Retrieve relevant chunks from Qdrant using semantic search and optional metadata filters.
Example JSON:
    {
      "query": "what does a robot sensor do?",
      "limit": 3,
      "subject": "robotics",
      "topic": "sensors",
      "subtopic": "environment sensing",
      "difficulty": 1,
      "lang": "en",
      "tags": ["sensor"]
    }
Returns:
- title
- content
- source
- score
- subject
- topic
- subtopic
- difficulty
- lang
- page
- chunk_id
- tags
---
## RAG Ask
Endpoint:
    POST /ask
Purpose:
Ask a question. The backend retrieves relevant chunks from Qdrant, sends them as context to the configured LLM provider, returns an answer, and logs the event.
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
Example response:
    {
      "question": "What parts of the robot does the battery power?",
      "answer": "Based on the provided context, the battery powers the controller, sensors, and motors.",
      "sources": [
        {
          "title": "Robotics Battery PDF Test",
          "source": "robotics-battery-test.pdf",
          "subject": "robotics",
          "topic": "power",
          "subtopic": "battery voltage and capacity",
          "difficulty": 2,
          "lang": "en",
          "chunk_id": "75085203-ca0b-4efa-a964-ed59d033483d",
          "tags": ["robotics", "battery", "pdf"]
        }
      ]
    }
---
## Progress Dashboard
Main endpoint:
    GET /progress/me
Purpose:
Returns the combined progress dashboard in one request.
It includes:
- summary
- subject-wise progress
- recent questions
- weak areas
- recommendations
Useful for:
- frontend dashboard
- n8n workflow integration
- student progress tracking
---
## Admin Content Management
Admin endpoints require this local/demo header:
    X-User-Role: admin
List content:
    GET /admin/content?limit=5&offset=0
Read one document:
    GET /admin/content/{document_id}
Create content:
    POST /admin/content
Update content:
    PATCH /admin/content/{document_id}
Delete content:
    DELETE /admin/content/{document_id}
Without the admin header, protected endpoints return:
    {
      "detail": "Admin access required."
    }
---
## Admin Content RAG Safety
Admin update/delete operations handle both PostgreSQL and Qdrant.
Update flow:
1. Read existing document.
2. Delete old Qdrant vectors.
3. Delete old PostgreSQL chunks.
4. Update document row.
5. Re-chunk updated content.
6. Store new vectors in Qdrant.
7. Store new chunk metadata in PostgreSQL.
Delete flow:
1. Read existing document.
2. Get related Qdrant point IDs.
3. Delete vectors from Qdrant.
4. Delete document and chunks from PostgreSQL.
This prevents deleted or outdated content from appearing in future RAG results.
---
## Proof and Handover Documents
This repo includes:
    PROOF_CHECKLIST.md
    THARUKA_WORK_SUMMARY.md
    BUDDY_BACKEND_API_INTEGRATION_GUIDE.md
Use these files for proof, review, frontend integration, and handover.
---
## Current Status
Working locally and tested:
- Docker services
- FastAPI backend
- PostgreSQL connection
- Qdrant connection
- Qdrant collection
- OpenAI 768-dimensional embeddings
- text ingestion
- file upload ingestion
- TXT/DOCX/PDF upload
- unsupported file rejection
- semantic search
- RAG ask
- provider-based answer generation with OpenAI as current provider and DeepSeek fallback
- event logging
- progress dashboard
- admin content APIs
- admin route protection
- final health checks
---
## Current Limitations
- PDF extraction works for text-based PDFs. Scanned PDFs need OCR.
- Admin protection is demo-level using `X-User-Role: admin`.
- Production should use JWT/session authentication and real role validation.
- Production multilingual quality depends on the final approved embedding provider and API access.
#   b u d d y - b a c k n d 
 
 

# Buddy Backend API Integration Guide - Tharuka
## Base URL
Local backend:
    http://localhost:8000
Swagger UI:
    http://localhost:8000/docs
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
Purpose:
Use this when the frontend or n8n already has raw text content.
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
Example curl:
    curl.exe -X POST "http://localhost:8000/ingest/text" -H "Content-Type: application/json" --data-binary "@ingest-robotics.json"
---
## File Upload Ingestion
Endpoint:
    POST /ingest/file
Purpose:
Use this when admin/frontend uploads a learning content file.
Supported file types:
- TXT
- MD
- PDF
- DOCX
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
    curl.exe -X POST "http://localhost:8000/ingest/file" -F "file=@robotics-battery-test.pdf" -F "title=Robotics Battery PDF Test" -F "source=robotics-battery-test.pdf" -F "subject=robotics" -F "topic=power" -F "subtopic=battery voltage and capacity" -F "difficulty=2" -F "lang=en" -F "tags=robotics,battery,pdf"
Example successful response:
    {
      "document_id": 16,
      "title": "Robotics Battery PDF Test",
      "source": "robotics-battery-test.pdf",
      "chunk_count": 1,
      "qdrant_point_ids": ["75085203-ca0b-4efa-a964-ed59d033483d"]
    }
Unsupported file response example:
    {
      "detail": "Unsupported file type '.csv'. Supported types: .docx, .md, .pdf, .txt"
    }
---
## Semantic Search
Endpoint:
    POST /search
Purpose:
Retrieve relevant learning content chunks from Qdrant.
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
Example curl:
    curl.exe -X POST "http://localhost:8000/search" -H "Content-Type: application/json" --data-binary "@search-test.json"
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
Ask a question. Backend retrieves relevant chunks and sends context to the configured LLM provider.
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
Example curl:
    curl.exe -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" --data-binary "@ask-pdf-test.json"
Example response:
    {
      "question": "What parts of the robot does the battery power?",
      "answer": "Based on the provided context, the battery powers the controller, sensors, and motors.",
      "sources": [
        {
          "title": "Robotics Battery PDF Test",
          "content": "[Page 1]\nRobotics Battery Lesson...",
          "source": "robotics-battery-test.pdf",
          "score": 0.59493434,
          "subject": "robotics",
          "topic": "power",
          "subtopic": "battery voltage and capacity",
          "difficulty": 2,
          "lang": "en",
          "page": null,
          "chunk_id": "75085203-ca0b-4efa-a964-ed59d033483d",
          "tags": ["robotics", "battery", "pdf"]
        }
      ]
    }
---
## Progress Dashboard
Endpoint:
    GET /progress/me
Purpose:
Frontend or n8n can use this single endpoint to get the full student progress dashboard.
Example:
    curl.exe "http://localhost:8000/progress/me"
Returns:
- summary
- progress by subject/topic/subtopic
- recent questions
- weak areas
- recommendations
---
## Admin Content List
Endpoint:
    GET /admin/content?limit=5&offset=0
Required header:
    X-User-Role: admin
Example:
    curl.exe "http://localhost:8000/admin/content?limit=5&offset=0" -H "X-User-Role: admin"
Purpose:
List ingested/uploaded learning content.
---
## Admin Content Detail
Endpoint:
    GET /admin/content/{document_id}
Required header:
    X-User-Role: admin
Example:
    curl.exe "http://localhost:8000/admin/content/16" -H "X-User-Role: admin"
Purpose:
View one document and its chunks.
---
## Admin Create Content
Endpoint:
    POST /admin/content
Required header:
    X-User-Role: admin
Purpose:
Admin manually adds learning content as text.
---
## Admin Update Content
Endpoint:
    PATCH /admin/content/{document_id}
Required header:
    X-User-Role: admin
Purpose:
Admin edits existing learning content.
Important:
Updating content deletes old Qdrant vectors and old chunks, then re-chunks and re-indexes the updated content.
---
## Admin Delete Content
Endpoint:
    DELETE /admin/content/{document_id}
Required header:
    X-User-Role: admin
Purpose:
Admin deletes learning content.
Important:
Deleting content removes both PostgreSQL document data and Qdrant vectors.
---
## Admin Auth Note
Current local/demo admin protection uses:
    X-User-Role: admin
Without this header, admin endpoints return:
    {
      "detail": "Admin access required."
    }
For production, this should be replaced with JWT/session-based authentication.
---
## Recommended Frontend/n8n Usage
Use `/ingest/file` for admin file uploads.
Use `/search` when the frontend only needs source chunks.
Use `/ask` when the frontend or n8n needs a final generated answer.
Use `/progress/me` for dashboard/progress screens.
Use `/admin/content` endpoints for admin content management screens.
---
## Current Backend Status
Confirmed working:
- Health check
- Qdrant connection
- PostgreSQL connection
- Text ingestion
- File upload ingestion
- TXT upload
- DOCX upload
- PDF upload
- Unsupported file rejection
- Semantic search
- RAG ask
- Event logging
- Progress dashboard
- Admin content list/detail/create/update/delete
- Admin route protection

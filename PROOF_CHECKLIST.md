# Tharuka Proof Checklist - Buddy AI Backend / RAG

## Current Runtime Configuration

Docker containers expected:
- buddy-postgres
- buddy-n8n
- buddy-qdrant

Qdrant:
- Dashboard: http://localhost:6333/dashboard
- Collection: course_content
- Vector size: 768
- Distance: Cosine
- HNSW: m=16, ef_construct=128
- Sparse vector BM25 enabled

Embedding:
- Provider: OpenAI
- Model: text-embedding-3-small
- Dimensions: 768

Backend:
- Swagger UI: http://127.0.0.1:8000/docs
- Start command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

PostgreSQL:
- Database: buddy_db
- User: buddy
- Expected tables:
  - documents
  - document_chunks
  - events

---

## Health Check Proof

Endpoint:
GET /health

Command:
curl http://localhost:8000/health

Confirmed response:
{"status":"ok","services":{"postgres":true,"qdrant":true}}

Status:
DONE

---

## Qdrant Collection Proof

Endpoint:
http://localhost:6333/collections

Expected:
- course_content collection exists

Confirmed:
- buddy_documents exists
- course_content exists

Status:
DONE

---

## OpenAI Embedding Proof

Command:
python -c "from app.embeddings import create_embedding; v=create_embedding('test robotics sensor lesson'); print(len(v)); print(v[:3])"

Expected:
768

Confirmed:
768

Status:
DONE

---

## Content Ingestion Proof

Endpoint:
POST /ingest/text

Test request:
{
  "title": "Robotics Sensor Test",
  "content": "A robot sensor detects things in the environment such as light, distance, temperature, or movement. The sensor sends this information to a controller so the robot can decide what action to take.",
  "source": "manual-robotics-test",
  "subject": "robotics",
  "topic": "sensors",
  "subtopic": "environment sensing",
  "difficulty": 1,
  "lang": "en",
  "tags": ["robotics", "sensor"]
}

Confirmed response:
{
  "document_id": 13,
  "title": "Robotics Sensor Test",
  "source": "manual-robotics-test",
  "chunk_count": 1,
  "qdrant_point_ids": ["081f5500-a06c-420c-8c57-40c2f850575d"]
}

Status:
DONE

---

## PostgreSQL Metadata Proof

Table:
document_chunks

Confirmed latest robotics chunk:
- document_id: 13
- source: manual-robotics-test
- subject: robotics
- topic: sensors
- subtopic: environment sensing
- difficulty: 1
- lang: en
- tags: {robotics,sensor}
- qdrant_point_id: 081f5500-a06c-420c-8c57-40c2f850575d

Status:
DONE

---

## Semantic Search Proof

Endpoint:
POST /search

Test question:
what information does a robot sensor detect?

Confirmed:
- Robotics Sensor Test returned
- source: manual-robotics-test
- score returned
- subject filter worked
- topic filter worked
- subtopic filter worked
- difficulty filter worked
- lang filter worked
- tags filter worked

Status:
DONE

---

## File Upload Ingestion Proof

Endpoint:
POST /ingest/file

Supported:
- TXT
- MD
- PDF
- DOCX

Test file:
robotics-upload-test.txt

Confirmed response:
{
  "document_id": 14,
  "title": "Robotics Ultrasonic Upload Test",
  "source": "robotics-upload-test.txt",
  "chunk_count": 1,
  "qdrant_point_ids": ["225658d1-1052-4fde-b802-b5973a05a3f8"]
}

Confirmed:
- TXT file upload accepted
- text extracted from uploaded file
- document saved in PostgreSQL
- chunk metadata saved in PostgreSQL
- vector saved in Qdrant
- uploaded content searchable through /search
- uploaded content answerable through /ask
- tags parsed from comma-separated form input

Status:
DONE

Additional file type tests:

DOCX test:
- file: robotics-motor-test.docx
- endpoint: POST /ingest/file
- document_id: 15
- title: Robotics Motor DOCX Test
- qdrant_point_id: f60bdffd-a7e7-4648-9054-cb387640d51f
- confirmed searchable through /search
- confirmed answerable through /ask
- status: DONE

PDF test:
- file: robotics-battery-test.pdf
- endpoint: POST /ingest/file
- document_id: 16
- title: Robotics Battery PDF Test
- qdrant_point_id: 75085203-ca0b-4efa-a964-ed59d033483d
- confirmed PDF text extraction with [Page 1] marker
- confirmed searchable through /search
- confirmed answerable through /ask
- status: DONE

PostgreSQL multi-file metadata proof:

Confirmed document_chunks rows for uploaded files:
- document_id 14: robotics-upload-test.txt
  - subject: robotics
  - topic: sensors
  - subtopic: ultrasonic distance sensing
  - tags: robotics, sensor, ultrasonic

- document_id 15: robotics-motor-test.docx
  - subject: robotics
  - topic: motors
  - subtopic: motor driver control
  - tags: robotics, motor, docx

- document_id 16: robotics-battery-test.pdf
  - subject: robotics
  - topic: power
  - subtopic: battery voltage and capacity
  - tags: robotics, battery, pdf

Status:
DONE

---

## Progress Dashboard After File Upload Tests

Endpoint:
GET /progress/me

Saved proof file:
progress-after-file-tests.json

Confirmed:
- total_questions increased to 8
- latest activity updated after PDF ask test
- TXT upload ask appears in recent_questions
- DOCX upload ask appears in recent_questions
- PDF upload ask appears in recent_questions
- robotics topics now include sensors, motors, and power
- robotics subtopics now include:
  - ultrasonic distance sensing
  - motor driver control
  - battery voltage and capacity

Status:
DONE

---

## Backend Route List Proof

Command:
python -c "from app.main import app; [print(route.path, sorted(route.methods)) for route in app.routes]"

Confirmed important routes:
- GET /health
- POST /ingest/text
- POST /ingest/file
- POST /search
- POST /ask
- GET /progress/me
- GET /admin/content
- GET /admin/content/{document_id}
- POST /admin/content
- PATCH /admin/content/{document_id}
- DELETE /admin/content/{document_id}

Status:
DONE

## Unsupported file rejection proof:

Test file:
unsupported-test.csv

Endpoint:
POST /ingest/file

Result:
{
  "detail": "Unsupported file type '.csv'. Supported types: .docx, .md, .pdf, .txt"
}

Confirmed:
- unsupported CSV upload rejected
- API returned a clear error message
- allowed file types are listed

Status:
DONE

---

## Admin Content API Proof

Admin list endpoint:
GET /admin/content?limit=5&offset=0

Header:
X-User-Role: admin

Confirmed:
- latest uploaded PDF, DOCX, and TXT files are visible
- document ids 16, 15, and 14 returned
- chunk_count returned for each document

Admin detail endpoint:
GET /admin/content/16

Confirmed:
- document metadata returned
- extracted PDF content returned
- chunk metadata returned
- Qdrant point ID returned
- subject/topic/subtopic/difficulty/lang/tags returned

Status:
DONE

## Admin authorization rejection proof:

Request:
GET /admin/content?limit=1&offset=0

Header:
none

Result:
{
  "detail": "Admin access required."
}

Confirmed:
- admin endpoint rejects requests without admin role header
- protected backend API behavior works

Status:
DONE

## RAG Ask Proof

Endpoint:
POST /ask

Test question:
What does a robot sensor detect and why does it send information to the controller?

Confirmed answer:
Based on the provided context, a robot sensor detects things in the environment such as light, distance, temperature, or movement. It sends this information to a controller so the robot can decide what action to take.

Confirmed sources:
- Dummy Robotics Lesson
- Robotics Sensor Test

Status:
DONE

---

## Event Logging Proof

Table:
events

Confirmed latest event:
- event_type: rag_ask
- question: What does a robot sensor detect and why does it send information to the controller?
- subject: robotics
- topic: sensors
- subtopic: environment sensing
- difficulty: 1
- lang: en
- tags: {sensor}
- source_count: 2
- source_chunk_ids:
  - 3287c484-34c6-4148-8088-2754fc3918d6
  - 081f5500-a06c-420c-8c57-40c2f850575d

Status:
DONE

---

---

## OpenAI Answer Generation Proof

Configuration:
- LLM_PROVIDER=openai
- OPENAI_CHAT_MODEL=gpt-4o-mini
- EMBEDDING_PROVIDER=openai
- OPENAI_EMBEDDING_MODEL=text-embedding-3-small

Endpoint tested:
POST /ask

Test file:
ask-pdf-test.json

Question:
What parts of the robot does the battery power?

Confirmed answer:
The battery powers the controller, sensors, and motors of the robot.

Confirmed:
- OpenAI answer generation works
- RAG still retrieves Qdrant source chunk
- PDF source chunk returned correctly
- DeepSeek fallback remains available through LLM_PROVIDER=deepseek

Status:
DONE

---

## Final System Health Proof

FastAPI health endpoint:
GET /health

Result:
{
  "status": "ok",
  "services": {
    "postgres": true,
    "qdrant": true
  }
}

Qdrant health endpoint:
GET http://localhost:6333/healthz

Result:
healthz check passed

Confirmed:
- FastAPI is running
- PostgreSQL connection is healthy
- Qdrant connection is healthy
- Qdrant service is responding directly

Status:
DONE

## Working API Endpoints

General:
- GET /
- GET /health

Document and RAG:
- POST /documents
- POST /ingest/text
- POST /search
- POST /ask

Progress:
- GET /events/recent
- GET /progress/summary
- GET /progress/by-subject
- GET /progress/recent-questions
- GET /progress/weak-areas
- GET /progress/recommendations
- GET /progress/me

Admin content:
- GET /admin/content
- GET /admin/content/{document_id}
- POST /admin/content
- PATCH /admin/content/{document_id}
- DELETE /admin/content/{document_id}

---

## Completed Proof Status

DONE:
- Docker services startup tested
- FastAPI backend startup tested
- Swagger UI tested
- PostgreSQL connection tested
- Qdrant connection tested
- course_content Qdrant collection created
- Qdrant vector size set to 768
- Qdrant cosine distance configured
- HNSW parameters configured
- BM25 sparse vector enabled
- OpenAI API key configured
- OpenAI text-embedding-3-small tested
- OpenAI 768-dimensional embedding tested
- Text ingestion tested
- Chunk creation tested
- Qdrant vector storage tested
- PostgreSQL document storage tested
- PostgreSQL chunk metadata storage tested
- Semantic search tested
- RAG ask flow tested
- Source metadata returned
- Subject filtering tested
- Topic filtering tested
- Subtopic filtering tested
- Tags filtering tested
- Language filtering tested
- Difficulty-aware retrieval tested
- Event logging tested

---

## Combined Progress Dashboard Proof

Endpoint:
GET /progress/me

Command:
curl.exe "http://localhost:8000/progress/me" -o progress-me-proof.json

Confirmed:
- status 200
- summary returned
- total_questions: 5
- subject_count: 3
- topic_count: 4
- subtopic_count: 4
- latest_activity returned
- by_subject returned
- recent_questions returned
- weak_areas returned
- recommendations returned
- robotics progress appears with topic sensors and subtopic environment sensing
- no-source weak area appears for previous unmatched Networking test

Status:
DONE

---

## Current Remaining Work

Remaining:
- Prepare frontend integration examples
- Prepare n8n workflow integration
- Add file upload support for PDF, DOCX, MD, and TXT
- Add retrieval evaluation such as hit-rate@5 and MRR
- Add full hybrid search implementation in backend code using dense + sparse + RRF
- Add query-time HNSW ef=64 if required through Qdrant search params
- Finalize production embedding model decision
- Evaluate production-quality multilingual embedding support
- Replace demo header-based admin protection with production JWT/session role validation
- Pin Docker image tags instead of using latest


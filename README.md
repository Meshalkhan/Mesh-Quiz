# Mesh Quiz

Quiz generation from your own documents. Upload one or more files -> pick a topic -> get multiple-choice questions where every question cites the source chunk it came from. A verifier drops any question the cited source does not support.

**Stack:** Next.js 15 (TypeScript, Tailwind, Motion) · FastAPI (Python 3.12) · ChromaDB · Groq (open models) · LangGraph and Amazon Bedrock (planned)

If the sources cannot support enough verified questions, the API says so instead of padding the quiz.

### Status

| Milestone | Status |
|-----------|--------|
| v0.1 thin slice (upload → topic → verified quiz) | Planned |
| LangGraph graph (generator → verifier loop) | Planned |
| Bedrock + Guardrails | Planned |
| Hybrid retrieval | Planned |
| Evaluation | Planned |

Today the repo holds the Mesh RAG foundation: upload, indexing, grounded chat with refusal by default, and the Groq provider. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Architecture

```text
Browser (Next.js · single-page workspace)
        │  HTTP
        ▼
FastAPI (/api/v1)
        ├── DocumentService → disk + DocumentProcessor → VectorStore (ChromaDB)
        ├── ChatService → VectorStore (retrieve by filename) → LLMProvider (Groq)
        └── QuizService (planned) → topics → generator → verifier → quiz
```

| Piece | Tech | Role |
|-------|------|------|
| UI | Next.js 15, TypeScript, Tailwind, Motion | `/` workspace: upload, select, chat, theme |
| API | FastAPI, Pydantic | Validation, orchestration |
| Processing | pypdf | Page text + character chunks |
| Vectors | ChromaDB (persistent) | Embed + cosine search |
| LLM | Groq (open models) via `LLMProvider` | Grounded generation; Bedrock planned |

Routes stay thin; logic lives in services (`DocumentService`, `DocumentProcessor`, `VectorStore`, `ChatService`, `LLMProvider`).

### API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/health` | Liveness + which LLM providers have keys configured |
| `GET` | `/api/v1/documents` | List indexed filenames + chunk counts |
| `POST` | `/api/v1/documents/upload` | Validate PDF → chunk → index |
| `DELETE` | `/api/v1/documents/{filename}` | Remove chunks (+ matching upload files) |
| `POST` | `/api/v1/chat` | **Dev only** (debugging aid): `{ question, filename, provider? }` → answer + sources |

Planned quiz endpoints are listed in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Quiz generation

Planned. Nothing below is implemented yet.

**Index:** extract page text → chunk (`CHUNK_SIZE` / `CHUNK_OVERLAP`) with `{filename, page_number}` → Chroma (default embeddings). This part exists today.

**Topics:** group the selected documents' chunks into topics the user can pick.

**Generate:** retrieve chunks for the topic → draft multiple-choice questions, each tied to the one chunk it came from.

**Verify:** check each question against its cited chunk; drop any that the chunk does not support. If fewer verified questions remain than requested, return an explicit "not enough support" response rather than padding.

**Refusal today:** `/chat` keeps Mesh RAG's behavior. If retrieval finds nothing within `RETRIEVAL_MAX_DISTANCE`, it returns exactly `I couldn't find relevant information.` and does not call the LLM (covered by `backend/tests/test_chat.py`).

### Persistence

- Documents: `UPLOAD_DIR` (default `storage/uploads`)
- Vectors: `CHROMA_PERSIST_DIR` (default `storage/chroma`)

---

## Local setup

### Prerequisites

- Node.js 20+
- Python 3.12 + [uv](https://github.com/astral-sh/uv)
- Groq API key

### 1. Environment

```bash
cp .env.example .env
# Set GROQ_API_KEY in .env

cp frontend/.env.example frontend/.env.local
```

### 2. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

API docs: http://127.0.0.1:8001/docs

Checks:

```bash
uv run ruff check .
uv run pytest
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

### Smoke check

1. http://127.0.0.1:8001/api/v1/health → `"service": "mesh-quiz-api"`, `groq` listed
2. Open http://localhost:3000 → **Upload PDF**
3. Select the document in the list
4. Ask a question covered by that file → confirm answer + sources
5. Ask something the file does not cover → `I couldn't find relevant information.`

---

## Environment variables

Root `.env` (backend reads `.env` / `../.env`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `APP_NAME` / `APP_VERSION` / `APP_ENV` | Service metadata | `mesh-quiz-api` / `0.1.0` / `development` |
| `API_V1_PREFIX` | API mount path | `/api/v1` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:3000` |
| `LOG_LEVEL` / `LOG_JSON` | Logging | `INFO` / `true` |
| `UPLOAD_DIR` | Document storage | `storage/uploads` |
| `MAX_UPLOAD_BYTES` | Upload size cap | `26214400` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking | `1000` / `200` |
| `CHROMA_PERSIST_DIR` | Vector DB path | `storage/chroma` |
| `CHROMA_COLLECTION_NAME` | Collection name | `documents` |
| `LLM_PROVIDER` | `groq` (only option today) | `groq` |
| `GROQ_API_KEY` | Groq auth | _(required)_ |
| `GROQ_MODEL` | Groq model id | `llama-3.3-70b-versatile` |
| `RETRIEVAL_TOP_K` | Neighbor count | `5` |
| `RETRIEVAL_MAX_DISTANCE` | Cosine distance cutoff | `0.7` |

Frontend:

| Variable | Purpose | Example |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base | `http://localhost:8001/api/v1` |

Templates: [`.env.example`](.env.example), [`frontend/.env.example`](frontend/.env.example)

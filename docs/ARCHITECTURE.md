# Mesh Quiz — Architecture

Mesh Quiz turns uploaded documents into source-grounded multiple-choice quizzes. It grows out of Mesh RAG and keeps its layout: thin FastAPI routes, logic in services, ChromaDB for vectors, LLM access behind one `LLMProvider` interface.

## Goals

- Every question cites the source chunk it came from (filename, page, chunk id).
- A verifier checks each question against its cited chunk and drops any it does not support.
- Refusal by default: if the sources cannot support enough verified questions, the API says so instead of padding the quiz.
- Swap model providers through configuration only; routes and services stay unchanged.
- Measurable quality: grounding, answer correctness and distractor quality tracked by an evaluation set.

## Non-goals (for now)

- User accounts, multi-tenant isolation, sharing.
- Free-text or open-ended question types; adaptive or spaced-repetition scheduling.
- Scanned or image-only documents (no OCR).
- Fine-tuning models.
- Production deployment (CI only; no deploy step).

## Planned data flow

```text
upload ──► topics ──► generator ──► verifier ──► quiz
  │          │            │             │          │
  │          │            │             │          └─ verified questions + citations,
  │          │            │             │             or a "not enough support" response
  │          │            │             └─ per question: does the cited chunk support the
  │          │            │                stem and the correct option? drop if not
  │          │            └─ retrieve chunks for the topic → draft MCQs, each tied to one chunk
  │          └─ cluster / summarise indexed chunks into pickable topics
  └─ validate → extract text → chunk with {filename, page, chunk_id} → embed → ChromaDB
```

Today the upload → index path exists (inherited from Mesh RAG). Topics, generator and verifier are planned; the generator → verifier loop becomes a LangGraph graph.

## API plan

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| `GET` | `/api/v1/health` | Exists | Liveness + configured LLM providers |
| `GET` | `/api/v1/documents` | Exists | List indexed documents |
| `POST` | `/api/v1/documents/upload` | Exists | Validate → chunk → index |
| `DELETE` | `/api/v1/documents/{filename}` | Exists | Remove chunks and stored file |
| `POST` | `/api/v1/chat` | Exists (dev only) | Grounded Q&A; debugging aid, not part of the quiz API |
| `GET` | `/api/v1/topics?filenames=` | Planned | Topics derived from selected documents |
| `POST` | `/api/v1/quizzes` | Planned | `{ filenames, topic, count }` → verified questions with citations, or an insufficient-sources response |
| `GET` | `/api/v1/quizzes/{id}` | Planned | Fetch a generated quiz |

## Model policy

- **Now:** open models on Groq, behind `LLMProvider` (`GroqProvider` is the only implementation).
- **Later:** Amazon Bedrock as a second provider, with one small Claude model and one open-weight model, plus Bedrock Guardrails. It is added as a new class registered in `app/services/llm.py`, with no route or service changes.
- **Benchmarks:** local BGE embeddings and a reranker are evaluated as extra rows against the default Chroma embeddings.
- No other model vendors: Groq and Bedrock are the only providers in scope.

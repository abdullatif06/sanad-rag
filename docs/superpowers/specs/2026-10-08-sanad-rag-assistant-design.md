# Sanad — Bilingual Document Assistant (Design Spec)

Date: 2026-10-08
Working name: **Sanad** (Arabic: "support" / chain of sources — fits the citation focus). Rename freely.

## 1. Purpose

A standalone portfolio product proving Abdullatif's "RAG Systems" service. A business uploads its documents and gets an assistant that answers in **Arabic or English with exact citations**, plus an **auto-generated accuracy report**. Visitors can try it live with their own files.

**Audience:** freelance clients (founders, businesses), mainly in Jordan / MENA.

**Success criteria**
- Live demo: upload a PDF → ask in Arabic or English → cited answer in under ~5s.
- Accuracy report generated automatically per document set, with real numbers.
- Embeddable widget working on any external site via one `<script>` tag.
- Public GitHub repo with clear README, architecture diagram, and eval results.
- Runs on free tiers (Gemini free tier, Supabase free, Cloudflare free, cheap/free backend host).

**Non-goals (YAGNI)**
- Billing, plans, teams/roles.
- Connectors (Google Drive, Notion, etc.) — file upload only.
- File types beyond PDF, DOCX, TXT/MD.
- Fine-tuning or self-hosted models.

## 2. Architecture

```
Next.js app (Cloudflare)          Widget (vanilla JS bundle)
   │ dashboard, demo, reports        │ chat bubble on client sites
   └──────────────┬──────────────────┘
                  ▼
          FastAPI backend (Python)
   ingest · retrieve · answer · evaluate
          │                    │
          ▼                    ▼
 Supabase (Postgres +      Gemini API
 pgvector, Auth, Storage)  (Flash for generation,
                            Gemini embeddings)
```

**Decisions**
- **LLM:** Gemini Flash (free tier) for answers, question generation, and eval judging.
- **Embeddings:** Gemini embedding model (multilingual, free tier) — one provider, one key.
- **Search:** hybrid — pgvector similarity + Postgres full-text — merged with Reciprocal Rank Fusion. Improves Arabic keyword/name matching where vectors alone miss.
- **Provider isolation:** all Gemini calls go through one `llm` module so the provider can be swapped (e.g. Claude for paying clients) without touching other code.

## 3. Components (backend)

Each is a small module with one job:

| Module | Does | Depends on |
|---|---|---|
| `parsing` | Extract text + page numbers from PDF/DOCX/TXT | pypdf / python-docx |
| `chunking` | Split text into overlapping chunks, keep page/section metadata; Arabic-aware normalization (alef/yaa/taa-marbuta variants, diacritics removed for search) | — |
| `llm` | Wraps Gemini: `embed(texts)`, `generate(prompt)`, retries + rate limiting | Gemini SDK |
| `store` | Read/write workspaces, documents, chunks, eval runs | Supabase |
| `retrieval` | Hybrid search → top-k chunks for a query | `store`, `llm` |
| `answering` | Builds grounded prompt, answers in the question's language, returns answer + cited chunk IDs; says "not found in documents" when unsupported | `retrieval`, `llm` |
| `evaluation` | Generates test Q&A from chunks, runs them through the pipeline, scores results | `answering`, `llm`, `store` |
| `api` | FastAPI routes, auth, rate limits | all above |

## 4. Data flow

**Ingest:** upload → store file in Supabase Storage → parse → chunk → embed in batches → save chunks → mark document `ready` (status shown live in UI).

**Ask:** question → detect language → hybrid retrieve top-k → Gemini answers using only those chunks → response with inline citation markers `[1]` → UI shows source passage + page on click.

**Evaluate:** sample chunks → Gemini writes ~20 Q&A pairs (mixed Arabic/English) → run each through Ask → score:
- **Retrieval hit rate** — was the source chunk retrieved?
- **Citation accuracy** — does the cited chunk support the answer?
- **Faithfulness** — LLM-judged: is the answer grounded, no invention?
- **Latency** — p50 / p95.

Results saved as an eval run and shown as a report page (shareable link).

## 5. Data model (Supabase)

- `workspaces` (id, owner_id, name, public_key, is_demo, created_at)
- `documents` (id, workspace_id, filename, status, page_count, created_at)
- `chunks` (id, document_id, content, content_normalized, page, embedding vector, tsvector)
- `eval_runs` (id, workspace_id, metrics json, created_at)
- `eval_items` (id, run_id, question, expected_chunk_id, answer, scores json)

Row-level security: owners see only their workspaces. Widget uses the workspace `public_key` (read-only ask access).

## 6. Frontend (Next.js)

- **Landing / live demo:** drag-drop a file, chat immediately, no signup. Demo workspaces auto-delete after 24h.
- **Dashboard (signed in):** workspaces, documents, chat, run evaluation, widget embed code.
- **Report page:** metrics cards + per-question table.
- **Widget:** small standalone JS bundle, RTL-aware, loads chat for a `public_key`.
- Full RTL support for Arabic UI and answers.

## 7. Error handling & limits

- Gemini free-tier rate limits: backend queues embedding batches with backoff; user sees "processing" status, not errors.
- Upload limits on demo: 3 files, 10 MB each, 200 pages total.
- Per-IP and per-key rate limits on Ask.
- Scanned PDFs with no text: clear message ("this PDF has no extractable text"); OCR out of scope.
- No relevant chunks → assistant says it can't find the answer instead of guessing.
- **Privacy note:** Gemini free tier may use inputs to improve Google's products. Demo page states this; paid client deployments switch to a paid tier/provider via the `llm` module.

## 8. Testing

- Unit tests: parsing, chunking, Arabic normalization, rank fusion, citation parsing.
- `llm` mocked in unit tests; one small live smoke test behind an env flag.
- API tests for ingest → ask → evaluate flow.
- A fixed bilingual sample document set + its eval run committed to the repo as a regression baseline and README showcase.

## 9. Deploy

- Frontend + widget: Cloudflare (same as portfolio).
- Backend: Railway / Fly.io / Render free tier, Dockerized.
- Supabase free project.
- Secrets via env vars only.

## 10. Build order

1. Backend core: parse → chunk → embed → store → hybrid search → cited answer (English).
2. Arabic support: normalization, full-text config, RTL, bilingual prompts.
3. Evaluation + report page.
4. Next.js dashboard + live demo.
5. Embeddable widget.
6. Deploy, README, architecture diagram, portfolio entry.

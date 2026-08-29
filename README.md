# VedaAI Assessment Extractor & Answer Mapping

Phase 1 establishes the monorepo layout, a runnable FastAPI service, validated backend data contracts, an environment blueprint, and a Supabase migration with private upload buckets. Document processing, Gemini calls, persistence endpoints, and the interactive UI belong to later phases.

Phase 2 adds a `POST /api/v1/parse` multipart endpoint. It rasterizes PDF, PNG, and JPEG input to 150-DPI JPEG pages, extracts ordered questions with Gemini, then transcribes and spatially maps every student answer. Results are returned only for review in this phase; Supabase persistence and automated scoring are intentionally deferred.

Phase 3 adds the Next.js teacher workspace in `frontend/`: upload/progress UI, status filters, question navigation, client-side PDF/image rendering, auto-scroll, and responsive normalized answer overlays. The review session is browser-local until Phase 4 persistence is added.

## Layout

- `backend/`: FastAPI service and contract tests.
- `frontend/`: reserved Next.js workspace for Phase 3.
- `supabase/`: database and storage migration.

## Run locally

From `backend/`, install dependencies into the supplied workspace virtual environment and start the API:

```powershell
..\..\viraj\Scripts\python.exe -m pip install -r requirements.txt
..\..\viraj\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

`http://localhost:8000/api/v1/health` works without third-party credentials. It reports both integrations as unconfigured until their variables are set.

## Configure Supabase

1. Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. The service-role key is backend-only and must never be exposed to the browser.
2. Apply everything in `supabase/migrations/` using the Supabase CLI or SQL editor. Together they create `assessments`, `questions`, `unmatched_answers`, their indexes, and the private `question-papers` / `answer-sheets` buckets.

To run the migrations from this repository, add the PostgreSQL connection URI from **Supabase Dashboard → Connect** as `SUPABASE_DB_URL` in `.env`, then run (it applies every migration in filename order and is safe to re-run):

```powershell
..\viraj\Scripts\python.exe backend\scripts\apply_migration.py
```

## Parsing API

Two ways to run the pipeline. The UI uses the job flow.

| Endpoint | Purpose |
| :--- | :--- |
| `POST /api/v1/parse/jobs` | Upload both documents, start the pipeline in the background, get a `job_id` back immediately (202). |
| `GET /api/v1/parse/jobs/{id}/events` | Server-Sent Events stream of stage transitions. Drives the progress UI (FR-02). |
| `GET /api/v1/parse/jobs/{id}` | Poll the same status. Used automatically when SSE cannot be established. |
| `GET /api/v1/parse/jobs/{id}/result` | Collect the finished `AssessmentResponse`. 409 while still running, or the job's own failure status. |
| `POST /api/v1/parse` | One-shot synchronous parse. No progress signal, and can exceed platform request timeouts on longer documents. |

Stages reported, in order: `uploading`, `rasterizing`, `parsing_questions`, `grounding_answers`, `persisting`.
Each status frame also carries a `detail` string (for example `Answer sheet page 3 of 4`) and a `progress`
fraction, so the client never has to guess where the pipeline is.

Failures carry the status they deserve rather than a single generic 502: `429` for an exhausted Gemini
quota, `504` on timeout, `503` when Gemini is unreachable, `422` for a page Gemini cannot read, `500`
for a rejected or missing API key, and `502` only for a genuinely unusable response.

**Job state is per-process.** It lives in memory in the worker that accepted the upload, which suits a
single uvicorn worker. Running multiple workers or replicas requires moving `JobStore` to Redis or
Postgres, or a poll can land on a worker that never saw the job.

## Security scope

This is a demo deployment, and its access control is scoped to match.

- **Reads are public.** Listing assessments and opening one needs no credential, so the app
  can be explored without a signup wall.
- **Writes require a shared key.** `POST /parse`, `POST /parse/jobs`, and
  `DELETE /assessments/{id}` require the `X-Demo-Key` header to match `DEMO_ACCESS_KEY`.
  Those are the operations that spend Gemini free-tier quota or destroy data.
- **Rate limiting is independent of the key.** `PARSE_RATE_LIMIT_PER_HOUR` caps parses per
  client IP, so the quota is protected even if the key is shared onwards.
- **The key is never in the client bundle.** `NEXT_PUBLIC_*` values are inlined at build
  time and would be readable by every visitor. The key is supplied per viewer instead —
  through `?key=…` on first load, or the in-app field — and kept in that browser's
  `localStorage`. A key in a URL is visible in history and referrer headers, which is an
  acceptable trade for a rotatable demo key and would not be for a real credential.

This gates cost and destruction, not identity. Real multi-tenancy would mean per-user
ownership on every row and Supabase RLS policies, which is a different product than the one
this repository describes; the `service_role` key stays strictly server-side either way.

With `DEMO_ACCESS_KEY` unset — the default, and how the test suite runs — every endpoint is
open and nothing is throttled.

## Test contracts

```powershell
..\viraj\Scripts\python.exe -m pytest backend/tests
```

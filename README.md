# VedaAI Assessment Extractor & Answer Mapping

An automated assessment extraction and evaluation system. It takes printed exam question papers alongside handwritten student answer sheets, parses and extracts questions, spatially grounds and maps each handwritten answer block to its corresponding question, evaluates student answers with constructive feedback and marks, and renders an interactive side-by-side review workspace.

## Project Structure

- `backend/`: FastAPI application handling PDF/image rasterization, Google Gemini Vision integration, background job execution, and Supabase persistence.
- `frontend/`: Next.js workspace with client-side document viewing, bounding-box overlays, live stage progress tracking, and score breakdown.
- `supabase/`: Database schemas, storage bucket policies, and SQL migrations.

## Getting Started

### 1. Backend Setup

From the repository root, install backend dependencies and start the API server:

```powershell
..\viraj\Scripts\python.exe -m pip install -r backend/requirements.txt
..\viraj\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

The health check endpoint at `http://localhost:8000/api/v1/health` verifies API status and reports whether third-party integrations (Gemini and Supabase) are configured.

### 2. Frontend Setup

From `frontend/`:

```powershell
npm install
npm run dev
```

The frontend will run at `http://localhost:3000`.

### 3. Environment & Supabase Configuration

1. Copy `.env.example` to `.env` and set your credentials:
   - `GEMINI_API_KEY`: API key from Google AI Studio.
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: Supabase project credentials.
2. Apply database migrations in `supabase/migrations/` using the Supabase CLI or SQL editor. To run them directly using the backend helper, set `SUPABASE_DB_URL` in `.env` and execute:

```powershell
..\viraj\Scripts\python.exe backend/scripts/apply_migration.py
```

## Parsing Pipeline

The backend supports both background job-based parsing (recommended for UI workflows) and direct synchronous parsing:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/parse/jobs` | `POST` | Upload question paper and answer sheet; returns a `job_id` immediately (202 Accepted). |
| `/api/v1/parse/jobs/{id}/events` | `GET` | Server-Sent Events (SSE) stream broadcasting live progress and stage transitions. |
| `/api/v1/parse/jobs/{id}` | `GET` | Polling endpoint for job status (used when SSE is not supported). |
| `/api/v1/parse/jobs/{id}/result` | `GET` | Retrieve completed assessment payload (returns 409 while processing). |
| `/api/v1/parse` | `POST` | Synchronous one-shot parse endpoint. |

### Pipeline Stages

During processing, the following stages are reported:
1. `uploading`: Document ingestion and staging.
2. `rasterizing`: Rendering PDF/image pages to standardized high-resolution images.
3. `parsing_questions`: Extracting structured questions, labels, subparts, and maximum marks.
4. `grounding_answers`: Transcribing handwritten answers, locating 2D bounding boxes on pages, and scoring.
5. `persisting`: Uploading source documents to storage and saving assessment records in PostgreSQL.

## Access Control & Rate Limiting

- **Read Operations**: Public endpoints for listing and viewing past assessments.
- **Write Operations**: When `DEMO_ACCESS_KEY` is configured in `.env`, mutating endpoints (`POST /parse`, `POST /parse/jobs`, `DELETE /assessments/{id}`) require the `X-Demo-Key` header.
- **Rate Limiting**: `PARSE_RATE_LIMIT_PER_HOUR` enforces per-IP sliding-window limits on parsing requests.
- **Client Key Handling**: Keys entered in the UI or passed via `?key=...` query parameters are stored in the browser's `localStorage` and never bundled at build time.

## Running Tests

Run the backend test suite:

```powershell
..\viraj\Scripts\python.exe -m pytest backend/tests
```


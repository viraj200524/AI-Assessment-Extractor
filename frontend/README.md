# Frontend

Phase 3 implements the teacher-facing Next.js workspace.

- `/`: selects question-paper and answer-sheet files, calls `POST /api/v1/parse`, and shows processing stages.
- `/assessment/[id]`: displays extracted questions beside the submitted answer document, filters by status, scrolls to the active page, and overlays the active normalized answer region.

The parsed assessment and local object URL remain in Zustand client state for this phase. Refreshing the review page intentionally returns the user to the upload flow; Phase 4 will retrieve persistent assessment records and assets from Supabase.

## Run locally

```powershell
npm.cmd install
npm.cmd run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` in the repository `.env` to the FastAPI base URL, normally `http://localhost:8000/api/v1`.

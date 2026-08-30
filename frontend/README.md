# VedaAI Assessment Extractor - Frontend

Next.js web client for uploading assessments, monitoring live extraction stages, and reviewing extracted questions with mapped student answers side-by-side.

## Application Routes

- `/`: Upload workspace for question papers and handwritten answer sheets with live stage progress tracking.
- `/assessment/[id]`: Interactive review workspace displaying parsed questions, scores, feedback, and document viewer with highlighted answer regions.
- `/history`: Historical assessments list with summary statistics and management actions.

## Getting Started

Install dependencies and start the development server:

```powershell
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

## Configuration

Set `NEXT_PUBLIC_API_BASE_URL` in the root `.env` to point to the backend API (defaults to `http://localhost:8000/api/v1`).


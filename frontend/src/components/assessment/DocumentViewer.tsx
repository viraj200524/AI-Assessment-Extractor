"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  LoaderCircle,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { BoundingBoxOverlay } from "@/components/assessment/BoundingBoxOverlay";
import type { QuestionItem } from "@/types";

interface DocumentViewerProps {
  documentUrl: string;
  documentType: string;
  questions: QuestionItem[];
  activeQuestionId: string | null;
}

export function DocumentViewer({
  documentUrl,
  documentType,
  questions,
  activeQuestionId,
}: DocumentViewerProps) {
  const [pageSources, setPageSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [isFitWidth, setIsFitWidth] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState<number>(1);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Render document pages from PDF or direct image
  useEffect(() => {
    let cancelled = false;

    async function preparePages() {
      setLoading(true);
      setError(null);

      try {
        if (documentType.startsWith("image/")) {
          if (!cancelled) {
            setPageSources([documentUrl]);
            setLoading(false);
          }
          return;
        }

        if (documentType !== "application/pdf") {
          throw new Error("Unsupported document type. Please upload a PDF, PNG, or JPEG.");
        }

        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url
        ).toString();

        const pdf = await pdfjs.getDocument(documentUrl).promise;
        const renderedPages: string[] = [];

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          const page = await pdf.getPage(pageNumber);
          const viewport = page.getViewport({ scale: 1.8 });
          const canvas = document.createElement("canvas");
          canvas.width = Math.ceil(viewport.width);
          canvas.height = Math.ceil(viewport.height);
          const context = canvas.getContext("2d");

          if (!context) {
            throw new Error("HTML5 Canvas is unavailable in this environment.");
          }

          await page.render({ canvas, canvasContext: context, viewport }).promise;
          renderedPages.push(canvas.toDataURL("image/jpeg", 0.92));
        }

        await pdf.destroy();

        if (!cancelled) {
          setPageSources(renderedPages);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(
            caughtError instanceof Error ? caughtError.message : "Unable to render this document."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void preparePages();

    return () => {
      cancelled = true;
    };
  }, [documentType, documentUrl]);

  const activeQuestion = questions.find((question) => question.id === activeQuestionId);

  // Auto-scroll to selected question's answer region
  useEffect(() => {
    const firstRegion = activeQuestion?.answer_regions?.[0];
    if (!firstRegion || !containerRef.current) return;

    const targetPageNumber = firstRegion.page_number;
    const pageElement = pageRefs.current.get(targetPageNumber);

    if (pageElement) {
      const container = containerRef.current;
      
      const pageOffsetTop = pageElement.offsetTop;
      const boxYMinRatio = firstRegion.box_2d.ymin / 1000;
      const boxOffsetInPage = pageElement.clientHeight * boxYMinRatio;
      
      const targetScrollY = Math.max(0, pageOffsetTop + boxOffsetInPage - 160);

      container.scrollTo({
        top: targetScrollY,
        behavior: "smooth",
      });

      setCurrentPage(targetPageNumber);
    }
  }, [activeQuestionId, activeQuestion]);

  // Track active page during manual scrolling
  const handleScroll = () => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const containerTop = container.scrollTop;

    let closestPage = 1;
    let minDistance = Infinity;

    pageRefs.current.forEach((el, pageNum) => {
      const pageTop = el.offsetTop;
      const distance = Math.abs(pageTop - containerTop);
      if (distance < minDistance) {
        minDistance = distance;
        closestPage = pageNum;
      }
    });

    setCurrentPage(closestPage);
  };

  const handleZoomIn = () => {
    setIsFitWidth(false);
    setZoomLevel((prev) => Math.min(prev + 15, 200));
  };

  const handleZoomOut = () => {
    setIsFitWidth(false);
    setZoomLevel((prev) => Math.max(prev - 15, 60));
  };

  const handleToggleFitWidth = () => {
    if (isFitWidth) {
      setIsFitWidth(false);
      setZoomLevel(100);
    } else {
      setIsFitWidth(true);
      setZoomLevel(100);
    }
  };

  const handleResetZoom = () => {
    setIsFitWidth(true);
    setZoomLevel(100);
  };

  if (loading) {
    return (
      <div className="grid h-full place-items-center text-slate-500 bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <LoaderCircle className="animate-spin text-blue-600" size={32} />
          <p className="text-sm font-semibold text-slate-600">Rendering document pages...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-6 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        <h3 className="font-bold text-base mb-1">Document Display Error</h3>
        <p>{error}</p>
      </div>
    );
  }

  const totalPages = pageSources.length;

  return (
    <section className="flex h-full flex-col bg-slate-100 overflow-hidden">
      {/* Figma Document Viewer Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-2.5 shadow-xs shrink-0">
        <div className="flex items-center gap-4 text-xs font-bold text-slate-700">
          <span className="rounded-lg bg-slate-100 px-3 py-1 text-slate-800 ring-1 ring-slate-200">
            Page {currentPage} of {totalPages}
          </span>
          <div className="hidden sm:flex items-center gap-1.5 text-blue-600">
            <Sparkles size={14} />
            <span className="font-semibold text-slate-600">
              {activeQuestion
                ? `Highlighting: Q ${activeQuestion.full_label}`
                : "Select a question to ground"}
            </span>
          </div>
        </div>

        {/* Zoom and Fit Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleZoomOut}
            disabled={zoomLevel <= 60 && !isFitWidth}
            className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-40 transition"
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
          <span className="min-w-[44px] text-center text-xs font-bold text-slate-700">
            {isFitWidth ? "Fit" : `${zoomLevel}%`}
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            disabled={zoomLevel >= 200}
            className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-40 transition"
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>

          <div className="h-4 w-px bg-slate-200 mx-1" />

          <button
            type="button"
            onClick={handleToggleFitWidth}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-bold transition ${
              isFitWidth
                ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                : "text-slate-600 hover:bg-slate-100"
            }`}
            title="Toggle Fit Width"
          >
            {isFitWidth ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            <span>Fit Width</span>
          </button>

          {!isFitWidth && zoomLevel !== 100 && (
            <button
              type="button"
              onClick={handleResetZoom}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
              title="Reset Zoom"
            >
              <RotateCcw size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Document Canvas Viewport */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="scrollbar-thin flex-1 overflow-y-auto p-5 sm:p-7"
      >
        <div
          className="mx-auto flex flex-col items-center transition-all duration-150"
          style={{
            width: isFitWidth ? "100%" : `${zoomLevel}%`,
            maxWidth: isFitWidth ? "850px" : "none",
          }}
        >
          {pageSources.map((source, index) => {
            const pageNumber = index + 1;
            return (
              <div
                key={`page-${pageNumber}-${source.slice(0, 32)}`}
                ref={(element) => {
                  if (element) {
                    pageRefs.current.set(pageNumber, element);
                  } else {
                    pageRefs.current.delete(pageNumber);
                  }
                }}
                className="page-card relative mb-6 w-full rounded-lg bg-white shadow-md border border-slate-200/80 overflow-hidden"
              >
                <img
                  src={source}
                  alt={`Student answer sheet page ${pageNumber}`}
                  className="block h-auto w-full select-none"
                  draggable={false}
                />

                {/* Spatial Bounding Box Canvas Overlay */}
                {activeQuestion && (
                  <BoundingBoxOverlay
                    regions={activeQuestion.answer_regions}
                    pageNumber={pageNumber}
                  />
                )}

                <div className="absolute bottom-3 right-3 rounded-md bg-slate-900/80 px-2.5 py-1 text-[11px] font-bold text-white shadow-sm backdrop-blur-xs">
                  Page {pageNumber}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

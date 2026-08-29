"use client";

import React from "react";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import type { JobStage } from "@/types";

interface ProcessingProgressProps {
  /** Index of the stage currently running; -1 before the first server update. */
  currentStage: number;
  stages: JobStage[];
  /** Sub-stage detail from the server, e.g. "Answer sheet page 3 of 4". */
  detail?: string | null;
  /** Fraction of the pipeline completed, 0..1. */
  progress?: number;
}

export function ProcessingProgress({
  currentStage,
  stages,
  detail,
  progress = 0,
}: ProcessingProgressProps) {
  const activeStage = stages[currentStage];
  const percent = Math.round(Math.min(Math.max(progress, 0), 1) * 100);

  return (
    <div
      className="mt-7 rounded-2xl border border-blue-100 bg-blue-50/80 p-5 shadow-xs"
      role="status"
      aria-live="polite"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-bold text-navy">
          <LoaderCircle className="animate-spin text-blue-600" size={18} />
          <span>{activeStage ? `${activeStage.label}...` : "Processing Assessment Pipeline..."}</span>
        </div>
        <span className="text-xs font-bold text-blue-700">
          Stage {Math.min(currentStage + 1, stages.length)} of {stages.length}
        </span>
      </div>

      {/* Overall pipeline progress reported by the server */}
      <div
        className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-blue-100"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {stages.map((stage, index) => {
          const isComplete = index < currentStage;
          const isCurrent = index === currentStage;

          return (
            <div
              key={stage.key}
              className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                isCurrent
                  ? "bg-blue-600 text-white shadow-sm ring-2 ring-blue-400/40"
                  : isComplete
                  ? "bg-emerald-100/80 text-emerald-800"
                  : "bg-white/80 text-slate-400"
              }`}
            >
              {isComplete ? (
                <CheckCircle2 size={15} className="shrink-0 text-emerald-600" />
              ) : isCurrent ? (
                <LoaderCircle size={15} className="shrink-0 animate-spin text-white" />
              ) : (
                <div className="h-2 w-2 rounded-full bg-slate-300 shrink-0" />
              )}
              <span className="truncate">{stage.label}</span>
            </div>
          );
        })}
      </div>

      {detail && (
        <p className="mt-3 truncate text-xs font-medium text-blue-700/90" title={detail}>
          {detail}
        </p>
      )}
    </div>
  );
}

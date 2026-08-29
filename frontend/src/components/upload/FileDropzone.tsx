"use client";

import React, { useRef, useState } from "react";
import { FileCheck, ImageUp, UploadCloud, X } from "lucide-react";

interface FileDropzoneProps {
  label: string;
  description: string;
  file: File | null;
  onChange: (file: File | null) => void;
  acceptedTypes?: string;
}

export function FileDropzone({
  label,
  description,
  file,
  onChange,
  acceptedTypes = "application/pdf,image/png,image/jpeg",
}: FileDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      onChange(droppedFile);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <section
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`dropzone relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition-all ${
        isDragOver
          ? "border-blue-500 bg-blue-50/70 scale-[1.01]"
          : file
          ? "border-blue-300 bg-blue-50/20"
          : "border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50/50"
      }`}
    >
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept={acceptedTypes}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />

      {file ? (
        <div className="flex flex-col items-center">
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-xl bg-blue-100 text-blue-700">
            <FileCheck size={26} />
          </div>
          <h3 className="text-sm font-bold text-ink">{label}</h3>
          <p className="mt-1 font-semibold text-xs text-blue-700 max-w-[260px] truncate">
            {file.name}
          </p>
          <span className="mt-0.5 text-[11px] text-slate-400 font-medium">
            {formatFileSize(file.size)}
          </span>

          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50"
            >
              Change file
            </button>
            <button
              type="button"
              onClick={() => onChange(null)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
              title="Remove file"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div className="mx-auto mb-3.5 grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-600">
            <UploadCloud size={24} />
          </div>
          <h3 className="text-base font-bold text-ink">{label}</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500 max-w-xs">{description}</p>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-bold text-blue-700 transition hover:bg-blue-100/70"
          >
            <ImageUp size={15} />
            <span>Browse or Drop File</span>
          </button>
          <p className="mt-3 text-[11px] font-medium text-slate-400">PDF, PNG, or JPEG (Max 50MB)</p>
        </div>
      )}
    </section>
  );
}

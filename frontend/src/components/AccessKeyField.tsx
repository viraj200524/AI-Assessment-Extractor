"use client";

import React, { useState } from "react";
import { CheckCircle2, KeyRound, X } from "lucide-react";
import { useAccessKey } from "@/hooks/useAccessKey";

/**
 * Compact access-key control. Renders nothing unless this deployment actually gates writes,
 * so local development and an unprotected deployment show no extra chrome.
 */
export function AccessKeyField({ className = "" }: { className?: string }) {
  const { required, resolved, hasKey, setKey, clear } = useAccessKey();
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);

  if (!resolved || !required) return null;

  if (hasKey && !editing) {
    return (
      <div className={`flex flex-wrap items-center gap-2 text-xs ${className}`}>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 font-bold text-emerald-700 ring-1 ring-emerald-200">
          <CheckCircle2 size={13} />
          Access key set
        </span>
        <button
          type="button"
          onClick={() => {
            clear();
            setDraft("");
            setEditing(true);
          }}
          className="inline-flex items-center gap-1 text-slate-400 transition hover:text-slate-600"
          title="Remove the stored access key"
        >
          <X size={13} />
          <span className="font-semibold">Clear</span>
        </button>
      </div>
    );
  }

  return (
    <form
      className={`flex flex-wrap items-center gap-2 ${className}`}
      onSubmit={(event) => {
        event.preventDefault();
        if (!draft.trim()) return;
        setKey(draft);
        setDraft("");
        setEditing(false);
      }}
    >
      <label className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600">
        <KeyRound size={14} className="text-blue-600" />
        Access key
      </label>
      <input
        type="password"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Paste the key from the submission"
        autoComplete="off"
        className="min-w-[220px] flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
      />
      <button
        type="submit"
        disabled={!draft.trim()}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        Save
      </button>
    </form>
  );
}

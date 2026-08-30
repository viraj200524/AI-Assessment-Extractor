"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Clock, FileText, ArrowUpRight, Trash2, Plus } from "lucide-react";
import { AccessKeyField } from "@/components/AccessKeyField";
import { listAssessments, deleteAssessmentById, AssessmentSummaryItem } from "@/lib/api";

export default function HistoryPage() {
  const [assessments, setAssessments] = useState<AssessmentSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const data = await listAssessments();
      setAssessments(data);
    } catch {
      setAssessments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchRecords();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this assessment record?")) return;

    setDeletingId(id);
    setDeleteError(null);
    try {
      await deleteAssessmentById(id);
      setAssessments((prev) => prev.filter((item) => item.id !== id));
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "The assessment could not be deleted.");
    } finally {
      setDeletingId(null);
    }
  };

  const getScoreBadgeClass = (pct: number) => {
    if (pct >= 75) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    if (pct >= 50) return "bg-blue-50 text-blue-700 ring-blue-200";
    return "bg-amber-50 text-amber-700 ring-amber-200";
  };

  return (
    <main className="app-shell min-h-screen bg-slate-50 p-6 sm:p-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-500 shadow-xs hover:bg-slate-50 transition"
              title="Return to Home"
            >
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="text-2xl font-extrabold text-ink">Assessment History</h1>
              <p className="text-sm text-slate-500">
                View past evaluated assessments, grading records, and answer mappings.
              </p>
            </div>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition"
          >
            <Plus size={15} />
            <span>New Assessment</span>
          </Link>
        </div>

        <AccessKeyField className="mb-5" />

        {deleteError && (
          <div
            role="alert"
            className="mb-5 rounded-xl border border-rose-200 bg-rose-50/90 px-4 py-3 text-xs font-semibold text-rose-800"
          >
            {deleteError}
          </div>
        )}

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500 shadow-xs">
            Loading assessment records from database...
          </div>
        ) : assessments.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-xs">
            <Clock className="mx-auto mb-3 text-slate-400" size={36} />
            <h3 className="font-bold text-ink text-base">No Saved Assessments Yet</h3>
            <p className="mt-1.5 text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              When you upload and extract an assessment, its results and grounded answer sheets will be stored in Supabase and listed here.
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-xs font-bold text-blue-700 hover:bg-blue-100/80 transition"
            >
              <FileText size={15} />
              <span>Start an Assessment</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/80 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4">Title</th>
                  <th className="px-6 py-4">Date</th>
                  <th className="px-6 py-4">Pages</th>
                  <th className="px-6 py-4">Score</th>
                  <th className="px-6 py-4">Percentage</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assessments.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/70 transition group">
                    <td className="px-6 py-4 font-bold text-ink">
                      <Link
                        href={`/assessment/${item.id}`}
                        className="hover:text-blue-600 transition"
                      >
                        {item.title}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(item.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {item.page_count} {item.page_count === 1 ? "page" : "pages"}
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-800">
                      {item.total_score} / {item.max_score}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-bold ring-1 ${getScoreBadgeClass(
                          item.percentage
                        )}`}
                      >
                        {item.percentage}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <Link
                          href={`/assessment/${item.id}`}
                          className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-bold text-blue-600 hover:bg-blue-50 transition"
                          title="Open Assessment Review"
                        >
                          <span>Review</span>
                          <ArrowUpRight size={14} />
                        </Link>
                        <button
                          type="button"
                          disabled={deletingId === item.id}
                          onClick={(e) => handleDelete(item.id, e)}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition disabled:opacity-50"
                          title="Delete Record"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

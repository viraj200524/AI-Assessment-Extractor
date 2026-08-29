"use client";

import React from "react";
import type { QuestionItem, QuestionStatus } from "@/types";

export type FilterOption = "all" | QuestionStatus;

interface FilterPillsProps {
  currentFilter: FilterOption;
  onFilterChange: (filter: FilterOption) => void;
  questions: QuestionItem[];
}

export function FilterPills({ currentFilter, onFilterChange, questions }: FilterPillsProps) {
  const counts = {
    all: questions.length,
    answered: questions.filter((q) => q.status === "answered").length,
    unanswered: questions.filter((q) => q.status === "unanswered").length,
    out_of_order: questions.filter((q) => q.status === "out_of_order").length,
  };

  const filterOptions: Array<{ value: FilterOption; label: string; count: number }> = [
    { value: "all", label: "All", count: counts.all },
    { value: "answered", label: "Answered", count: counts.answered },
    { value: "unanswered", label: "Unanswered", count: counts.unanswered },
    { value: "out_of_order", label: "Out of order", count: counts.out_of_order },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {filterOptions.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onFilterChange(item.value)}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold transition ${
            currentFilter === item.value
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          <span>{item.label}</span>
          <span
            className={`rounded-full px-1.5 py-0.2 text-[10px] ${
              currentFilter === item.value ? "bg-white/20 text-white" : "bg-slate-200 text-slate-700"
            }`}
          >
            {item.count}
          </span>
        </button>
      ))}
    </div>
  );
}

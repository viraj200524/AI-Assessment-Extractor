"use client";

import { useCallback } from "react";
import type { AnswerRegion } from "@/types";

export function useScrollToPage(pageRefs: React.MutableRefObject<Map<number, HTMLDivElement>>) {
  const scrollToRegion = useCallback(
    (regions: AnswerRegion[]) => {
      if (!regions || regions.length === 0) return;
      const targetPageNumber = regions[0].page_number;
      const targetElement = pageRefs.current.get(targetPageNumber);

      if (targetElement) {
        targetElement.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    },
    [pageRefs]
  );

  return { scrollToRegion };
}

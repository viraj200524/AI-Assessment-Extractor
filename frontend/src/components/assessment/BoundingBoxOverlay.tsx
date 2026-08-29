"use client";

import React from "react";
import { getBoundingBoxStyle } from "@/lib/coordinates";
import type { AnswerRegion } from "@/types";

interface BoundingBoxOverlayProps {
  regions: AnswerRegion[];
  pageNumber: number;
}

export function BoundingBoxOverlay({ regions, pageNumber }: BoundingBoxOverlayProps) {
  const pageRegions = regions.filter((region) => region.page_number === pageNumber);

  if (pageRegions.length === 0) return null;

  return (
    <>
      {pageRegions.map((region, index) => (
        <div
          key={`bbox-${pageNumber}-${index}`}
          className="answer-overlay"
          style={getBoundingBoxStyle(region.box_2d)}
          aria-label={`Answer region ${index + 1} on page ${pageNumber}`}
        />
      ))}
    </>
  );
}

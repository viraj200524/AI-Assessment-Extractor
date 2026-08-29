import type { CSSProperties } from "react";

import type { BoundingBox } from "@/types";

export function getBoundingBoxStyle(box: BoundingBox): CSSProperties {
  return {
    top: `${box.ymin / 10}%`,
    left: `${box.xmin / 10}%`,
    width: `${(box.xmax - box.xmin) / 10}%`,
    height: `${(box.ymax - box.ymin) / 10}%`,
  };
}

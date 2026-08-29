/**
 * Utility functions for frontend styling and class manipulation.
 */

export function cn(...inputs: Array<string | undefined | null | false>): string {
  return inputs.filter(Boolean).join(" ");
}

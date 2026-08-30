/**
 * Utilities for storing and retrieving the optional demo access key in the browser.
 */

const STORAGE_KEY = "vedai.accessKey";
const URL_PARAM = "key";

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readAccessKey(): string | null {
  try {
    return storage()?.getItem(STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

export function saveAccessKey(key: string): void {
  const trimmed = key.trim();
  try {
    if (trimmed) storage()?.setItem(STORAGE_KEY, trimmed);
    else storage()?.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage write errors (e.g. private browsing storage limits)
  }
}

export function clearAccessKey(): void {
  try {
    storage()?.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage deletion errors
  }
}

/**
 * Check for an access key in URL search parameters, store it, and clean the URL.
 */
export function bootstrapAccessKeyFromUrl(): boolean {
  if (typeof window === "undefined") return false;

  const url = new URL(window.location.href);
  const supplied = url.searchParams.get(URL_PARAM);
  if (!supplied) return false;

  saveAccessKey(supplied);
  url.searchParams.delete(URL_PARAM);
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  return true;
}

/**
 * Return authorization headers for mutating requests if a key is stored.
 */
export function accessKeyHeaders(): Record<string, string> {
  const key = readAccessKey();
  return key ? { "X-Demo-Key": key } : {};
}

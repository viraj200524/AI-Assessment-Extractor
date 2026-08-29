/**
 * Shared demo access key, held only in the viewer's browser.
 *
 * Deliberately NOT a NEXT_PUBLIC_ env var: those are inlined into the client bundle at
 * build time, so the key would ship in plain JavaScript to every visitor and protect
 * nothing. It is supplied per-viewer instead - via the `?key=` link or the in-app field -
 * and kept in localStorage.
 */

const STORAGE_KEY = "vedai.accessKey";
const URL_PARAM = "key";

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    // Private mode or blocked site data.
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
    /* nothing we can do; the request will just be rejected */
  }
}

export function clearAccessKey(): void {
  try {
    storage()?.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Adopt a key passed as `?key=...`, then strip it from the URL.
 *
 * This is what makes a single submitted link work with no setup. The trade-off is that a
 * URL-borne key is visible in browser history and referrer headers, which is acceptable for
 * a rotatable demo key and would not be for a real credential.
 *
 * Returns true when a key was adopted from the URL.
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

/** Headers for a mutating request. Empty when no key is held. */
export function accessKeyHeaders(): Record<string, string> {
  const key = readAccessKey();
  return key ? { "X-Demo-Key": key } : {};
}

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  bootstrapAccessKeyFromUrl,
  clearAccessKey,
  readAccessKey,
  saveAccessKey,
} from "@/lib/accessKey";
import { getHealth } from "@/lib/api";

/**
 * Tracks whether this deployment requires a shared access key, and whether the viewer holds
 * one. The key itself never comes from the bundle - it arrives via the `?key=` link or the
 * in-app field and lives only in this browser.
 */
export function useAccessKey() {
  const [required, setRequired] = useState<boolean | null>(null);
  const [key, setKeyState] = useState<string | null>(null);

  useEffect(() => {
    // Adopt a key from the URL before reading it back, so a fresh link works immediately.
    bootstrapAccessKeyFromUrl();
    setKeyState(readAccessKey());

    let cancelled = false;
    void getHealth().then((health) => {
      if (!cancelled) setRequired(health?.access_key_required ?? false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const setKey = useCallback((value: string) => {
    saveAccessKey(value);
    setKeyState(readAccessKey());
  }, []);

  const clear = useCallback(() => {
    clearAccessKey();
    setKeyState(null);
  }, []);

  return { required: required ?? false, resolved: required !== null, hasKey: Boolean(key), key, setKey, clear };
}

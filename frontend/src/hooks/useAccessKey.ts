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
 * Hook to manage demo access key status and browser storage.
 */
export function useAccessKey() {
  const [required, setRequired] = useState<boolean | null>(null);
  const [key, setKeyState] = useState<string | null>(null);

  useEffect(() => {
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

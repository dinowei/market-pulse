"use client";

// Stale-while-revalidate for read-only API answers: going back to a page shows what was already
// loaded at once and refreshes behind it. In memory only, so the owner's real data never reaches
// disk; login and logout clear it (clearApiCache).
import { useCallback, useEffect, useState } from "react";

import { apiRequest, isAbort, subscribeCacheClear } from "./api-client";

const memory = new Map<string, { at: number; value: unknown }>();
subscribeCacheClear(() => memory.clear());

export function useCachedApi<T>(path: string, ttlMs = 60_000) {
  const [state, setState] = useState<{ path: string; data?: T; failed?: boolean }>(() => ({ path, data: memory.get(path)?.value as T | undefined }));
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => {
    memory.delete(path);
    setTick((value) => value + 1);
  }, [path]);

  useEffect(() => {
    const cached = memory.get(path);
    if (cached && Date.now() - cached.at < ttlMs) return undefined;
    const controller = new AbortController();
    apiRequest<T>(path, { signal: controller.signal })
      .then((value) => {
        memory.set(path, { at: Date.now(), value });
        setState({ path, data: value });
      })
      .catch((error: unknown) => {
        if (!isAbort(error)) setState((current) => (current.path === path && current.data !== undefined ? current : { path, failed: true }));
      });
    return () => controller.abort();
  }, [path, ttlMs, tick]);

  const current = state.path === path ? state : { path, data: memory.get(path)?.value as T | undefined };
  return { data: current.data, failed: Boolean(current.failed), refresh };
}

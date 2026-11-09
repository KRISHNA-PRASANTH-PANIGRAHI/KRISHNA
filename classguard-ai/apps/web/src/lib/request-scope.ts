"use client";

import { useEffect, useRef } from "react";

// Each mounted account/institution scope owns its requests.
export function useRequestLifetime() {
  const lifetime = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    lifetime.current = controller;
    return () => controller.abort();
  }, []);
  return lifetime;
}

export function requestMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

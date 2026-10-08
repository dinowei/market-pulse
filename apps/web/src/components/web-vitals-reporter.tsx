"use client";

import { useEffect } from "react";

type Metric = "LCP" | "INP" | "CLS";

function report(metric: Metric, value: number): void {
  if (!Number.isFinite(value) || value < 0) return;
  const payload = JSON.stringify({
    metric,
    value: String(value),
    route: window.location.pathname || "/",
    sample_count: 1,
    observed_at: new Date().toISOString(),
  });
  const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/telemetry/web-vitals`;
  if (navigator.sendBeacon) {
    navigator.sendBeacon(endpoint, new Blob([payload], { type: "application/json" }));
    return;
  }
  void fetch(endpoint, { method: "POST", body: payload, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => undefined);
}

export function WebVitalsReporter() {
  useEffect(() => {
    if (typeof PerformanceObserver === "undefined") return undefined;
    const observers: PerformanceObserver[] = [];
    let cls = 0;
    let lcpReported = false;
    try {
      const lcp = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries.at(-1);
        if (last && !lcpReported) report("LCP", last.startTime);
        lcpReported = Boolean(last);
      });
      lcp.observe({ type: "largest-contentful-paint", buffered: true });
      observers.push(lcp);
    } catch { /* browser does not expose this metric */ }
    try {
      const inp = new PerformanceObserver((list) => {
        const last = list.getEntries().at(-1);
        if (last) report("INP", (last as PerformanceEventTiming).duration);
      });
      inp.observe({ type: "event", buffered: true, durationThreshold: 40 } as PerformanceObserverInit);
      observers.push(inp);
    } catch { /* browser does not expose this metric */ }
    try {
      const layout = new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as (PerformanceEntry & { value?: number; hadRecentInput?: boolean })[]) {
          if (!entry.hadRecentInput) cls += entry.value ?? 0;
        }
        report("CLS", cls);
      });
      layout.observe({ type: "layout-shift", buffered: true });
      observers.push(layout);
    } catch { /* browser does not expose this metric */ }
    return () => observers.forEach((observer) => observer.disconnect());
  }, []);
  return null;
}

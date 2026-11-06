"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

// Mounts heavy, provider-hungry sections only when the reader gets near them.
export function OnView({ children, label }: { children: ReactNode; label: string }) {
  const anchor = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const node = anchor.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      const timer = setTimeout(() => setVisible(true));
      return () => clearTimeout(timer);
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) setVisible(true);
    }, { rootMargin: "500px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return <div ref={anchor}>{visible ? children : <p className="muted">{label}</p>}</div>;
}

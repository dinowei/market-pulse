// Inline stroke icons (24×24), drawn for this project: no icon font, no extra download.
// Decorative by default; the control next to them always carries the accessible name.
import type { ReactNode, SVGProps } from "react";

const PATHS: Record<string, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>,
  markets: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /></>,
  chart: <><path d="M7 4v3M7 17v3M17 7v3M17 18v2" /><rect x="5" y="7" width="4" height="10" rx="1" /><rect x="15" y="10" width="4" height="8" rx="1" /></>,
  compare: <><path d="M3 17l5-6 4 3 4-7 5 5" /><path d="M3 21h18" opacity=".5" /></>,
  heatmap: <><rect x="3" y="3" width="10" height="8" rx="1.5" /><rect x="15" y="3" width="6" height="8" rx="1.5" /><rect x="3" y="13" width="6" height="8" rx="1.5" /><rect x="11" y="13" width="10" height="8" rx="1.5" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>,
  list: <><path d="M12 3l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8-4.3-4.1 5.9-.8z" /></>,
  wallet: <><path d="M4 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11" /><path d="M16 13.5h2" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>,
  login: <><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 16l4-4-4-4M14 12H3" /></>,
  logout: <><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 16l4-4-4-4M20 12H9" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></>,
  eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  morning: <><path d="M4 18h16M6 14a6 6 0 0 1 12 0M12 4v3M4.6 8.6l1.8 1.4M19.4 8.6 17.6 10" /></>,
  cursor: <><path d="M12 3v18M3 12h18" /></>,
  trend: <><circle cx="5" cy="19" r="2" /><circle cx="19" cy="5" r="2" /><path d="M6.5 17.5l11-11" /></>,
  ray: <><circle cx="5" cy="19" r="2" /><circle cx="13" cy="11" r="2" /><path d="M6.5 17.5 21 3" /></>,
  info: <><circle cx="5" cy="17" r="2" /><circle cx="17" cy="5" r="2" /><path d="M6.4 15.6 15.6 6.4" /><rect x="11" y="14" width="10" height="6" rx="1.5" /></>,
  extended: <><circle cx="9" cy="15" r="2" /><circle cx="15" cy="9" r="2" /><path d="M2 22 22 2" /></>,
  angle: <><path d="M4 20h16M4 20 18 6" /><path d="M11 20a7 7 0 0 0-2-5" /></>,
  hline: <><path d="M2 12h20" /><circle cx="12" cy="12" r="2" /></>,
  hray: <><path d="M10 12h12" /><circle cx="8" cy="12" r="2" /></>,
  vline: <><path d="M12 2v20" /><circle cx="12" cy="12" r="2" /></>,
  cross: <><path d="M12 2v20M2 12h20" /><circle cx="12" cy="12" r="2" /></>,
  channel: <><path d="M3 15 15 3M9 21 21 9" /><circle cx="3" cy="15" r="1.5" /><circle cx="21" cy="9" r="1.5" /></>,
  regression: <><path d="M3 18 21 6" /><path d="M3 14 21 2M3 22 21 10" strokeDasharray="2 2" /></>,
  fib: <><path d="M3 4h18M3 9h18M3 13h18M3 20h18" /><path d="M6 20 18 4" strokeDasharray="2 2" /></>,
  rect: <><rect x="4" y="6" width="16" height="12" rx="1" /></>,
  text: <><path d="M5 5h14M12 5v15M9 20h6" /></>,
  measure: <><path d="M4 20 20 4M7 17l1.5 1.5M10 14l1.5 1.5M13 11l1.5 1.5M16 8l1.5 1.5" /></>,
  magnet: <><path d="M6 3v8a6 6 0 0 0 12 0V3M6 7h3M15 7h3" /></>,
  lock: <><rect x="5" y="10" width="14" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
  hide: <><path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.8M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 4.4-1" /></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  fullscreen: <><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></>,
  indicators: <><path d="M3 17c3 0 3-10 6-10s3 10 6 10 3-6 6-6" /></>,
  layers: <><path d="M12 3 2 8l10 5 10-5z" /><path d="M2 13l10 5 10-5" opacity=".6" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  close: <><path d="M6 6l12 12M18 6 6 18" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  undo: <><path d="M9 14 4 9l5-5" /><path d="M4 9h10a6 6 0 0 1 0 12h-3" /></>,
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>
      {PATHS[name]}
    </svg>
  );
}

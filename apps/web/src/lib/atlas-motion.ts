// Particle Atlas motion layer (P1, ADR-023). Motion marks a transition — new asset,
// period, mode, chart type, tab or refresh — and then stops; it never encodes a price.
// `NEXT_PUBLIC_ATLAS_MOTION=off` removes it at build time, and the global
// prefers-reduced-motion rule in globals.css shortens every animation to ~0.
export const ATLAS_MOTION_ENABLED = process.env.NEXT_PUBLIC_ATLAS_MOTION !== "off";

export function motionClass(enabled: boolean = ATLAS_MOTION_ENABLED): string {
  return enabled ? " atlas-motion" : "";
}

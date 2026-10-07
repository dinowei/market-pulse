import type { components } from "../generated/api";

type SeriesDownsampling = components["schemas"]["SeriesDownsampling"];

/** Points requested for the main chart; the API returns the full series when it is shorter. */
export const DISPLAY_MAX_POINTS = 500;

/** Disclosure for a reduced series (directive section 19: no data disappears silently). */
export function downsamplingSummary(downsampling: SeriesDownsampling | null | undefined): string | undefined {
  if (!downsampling) return undefined;
  return (
    `Exibindo ${downsampling.returned_points} de ${downsampling.original_points} pontos. ` +
    "Redução M4 para exibição: primeiro, último, mínimo e máximo de cada intervalo e todos os gaps " +
    "foram preservados; nenhum ponto foi criado ou suavizado."
  );
}

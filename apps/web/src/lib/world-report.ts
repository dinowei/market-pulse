import type { components } from "../generated/api";
import { DIRECTION_CUE, type PriceDirection, priceDirection } from "./price-direction";

type WorldRegion = components["schemas"]["WorldRegion"];

export function regionDirection(region: Pick<WorldRegion, "change_percent">): PriceDirection | null {
  return priceDirection(region.change_percent);
}

/** Big number of a square: sign, glyph and word, so color is never the only cue. */
export function regionChange(percent: string | null | undefined): { direction: PriceDirection; value: string; word: string; glyph: string } | null {
  const direction = priceDirection(percent);
  if (!direction || percent == null) return null;
  const rounded = Math.abs(Number(percent)).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sign = direction === "UP" ? "+" : direction === "DOWN" ? "−" : "";
  return { direction, value: `${sign}${rounded}%`, word: DIRECTION_CUE[direction].word, glyph: DIRECTION_CUE[direction].glyph };
}

/** The hero's sentence, counted over the regions that have a measure. */
export function worldHeadline(regions: readonly Pick<WorldRegion, "title" | "change_percent">[]): string {
  const known = regions.filter((region) => regionDirection(region));
  if (known.length === 0) return "Ainda sem fechamentos para mostrar";
  const up = known.filter((region) => regionDirection(region) === "UP").length;
  const down = known.filter((region) => regionDirection(region) === "DOWN").length;
  return `${up} de ${known.length} regiões em alta, ${down} em queda`;
}

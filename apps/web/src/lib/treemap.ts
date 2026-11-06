// Squarified treemap (Bruls, Huizing and van Wijk): areas proportional to the value, with tiles
// as close to square as the order allows. Pure geometry, no market logic.
export type Rect = { x: number; y: number; width: number; height: number };

function worstRatio(row: readonly number[], side: number): number {
  const sum = row.reduce((total, value) => total + value, 0);
  const max = Math.max(...row);
  const min = Math.min(...row);
  return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
}

/** Rects in the input's order. Non-positive values get an empty rect at the origin. */
export function squarify(values: readonly number[], box: Rect): Rect[] {
  const total = values.reduce((sum, value) => sum + (value > 0 ? value : 0), 0);
  const rects: Rect[] = values.map(() => ({ x: box.x, y: box.y, width: 0, height: 0 }));
  if (total <= 0 || box.width <= 0 || box.height <= 0) return rects;
  const scale = (box.width * box.height) / total;
  const order = values.map((value, index) => ({ area: value * scale, index })).filter((item) => item.area > 0).sort((a, b) => b.area - a.area);

  let { x, y, width, height } = box;
  let start = 0;
  while (start < order.length) {
    const side = Math.min(width, height);
    const row = [order[start].area];
    let end = start + 1;
    while (end < order.length && worstRatio([...row, order[end].area], side) <= worstRatio(row, side)) {
      row.push(order[end].area);
      end += 1;
    }
    const sum = row.reduce((total2, value) => total2 + value, 0);
    const thickness = sum / side;
    let offset = 0;
    for (let index = start; index < end; index += 1) {
      const length = order[index].area / thickness;
      rects[order[index].index] = width >= height
        ? { x, y: y + offset, width: thickness, height: length }
        : { x: x + offset, y, width: length, height: thickness };
      offset += length;
    }
    if (width >= height) { x += thickness; width -= thickness; } else { y += thickness; height -= thickness; }
    start = end;
  }
  return rects;
}

/** Color step of a percent change: 0 is flat, 1 to 4 grow with the size of the move. */
export function changeStep(percent: number): number {
  const size = Math.abs(percent);
  if (size === 0) return 0;
  if (size < 0.5) return 1;
  if (size < 1.5) return 2;
  if (size < 3) return 3;
  return 4;
}

/** Height of a block in the 3D view, in pixels: taller for bigger moves, capped. */
export function blockHeight(percent: number | null): number {
  return percent === null ? 4 : Math.min(8 + Math.abs(percent) * 6, 38);
}

/** Softly rounded, never sharp or pill-heavy — reads as warm/premium rather
 * than playful. Buttons/inputs use the smaller end; image cards use the
 * larger end so photography reads as the hero content. */
export const radius = {
  none: 0,
  sm: 6,
  md: 10,
  lg: 16,
  xl: 24,
  full: 9999,
} as const;

export type RadiusKey = keyof typeof radius;

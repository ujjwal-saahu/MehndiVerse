/**
 * Type system: a warm display serif for headings (editorial, premium,
 * culturally resonant without being literal) paired with a clean geometric
 * sans for body/UI text (legible at small sizes, works well in dense admin
 * tables as well as marketing pages).
 */
export const fontFamily = {
  display: '"Fraunces", "Georgia", serif',
  body: '"Manrope", "Inter", system-ui, sans-serif',
} as const;

export const fontWeight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

/** size in px, lineHeight as a unitless multiplier, letterSpacing in em. */
export const fontSize = {
  xs: { size: 12, lineHeight: 1.5, letterSpacing: 0 },
  sm: { size: 14, lineHeight: 1.5, letterSpacing: 0 },
  base: { size: 16, lineHeight: 1.6, letterSpacing: 0 },
  lg: { size: 18, lineHeight: 1.6, letterSpacing: 0 },
  xl: { size: 20, lineHeight: 1.5, letterSpacing: -0.01 },
  "2xl": { size: 24, lineHeight: 1.4, letterSpacing: -0.01 },
  "3xl": { size: 30, lineHeight: 1.3, letterSpacing: -0.015 },
  "4xl": { size: 38, lineHeight: 1.2, letterSpacing: -0.02 },
  "5xl": { size: 48, lineHeight: 1.15, letterSpacing: -0.02 },
} as const;

export type FontSizeKey = keyof typeof fontSize;

export const typography = { fontFamily, fontWeight, fontSize } as const;

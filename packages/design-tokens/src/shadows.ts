/** Warm-tinted shadows (rgba of the deep sand/brown, not pure black) so
 * elevation reads as soft and premium rather than harsh. Expressed as CSS
 * box-shadow strings for direct use in web/admin; Flutter mirrors the same
 * offset/blur/color values as BoxShadow. */
const tint = (opacity: number) => `rgba(43, 33, 29, ${opacity})`;

export const shadows = {
  none: "none",
  xs: `0 1px 2px ${tint(0.06)}`,
  sm: `0 2px 4px ${tint(0.08)}`,
  md: `0 4px 10px ${tint(0.1)}`,
  lg: `0 10px 24px ${tint(0.12)}`,
  xl: `0 20px 40px ${tint(0.16)}`,
} as const;

export type ShadowKey = keyof typeof shadows;

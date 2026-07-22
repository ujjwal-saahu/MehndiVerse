/** Min-width breakpoints in px, shared by web/admin (Tailwind) and Flutter
 * (LayoutBuilder-driven responsive shells). */
export const breakpoints = {
  sm: 480,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type BreakpointKey = keyof typeof breakpoints;

/**
 * Primitive color scales for the MehndiVerse visual identity.
 *
 * Design direction: elegant, premium, warm, culturally resonant without
 * being kitschy. `henna` (a deep wine/oxblood maroon) is the brand color —
 * evoking henna stain without literally using "henna orange" cliché tones.
 * `marigold` is a restrained gold accent used sparingly (marigold garlands
 * are a recurring motif in South Asian bridal/festival imagery). `sand` is
 * the warm neutral scale used for backgrounds and text instead of cold
 * greys, keeping the whole palette warm-toned end to end.
 *
 * Each scale runs 50 (lightest) -> 950 (darkest), the standard convention
 * shared by Tailwind-style design systems, so the same numeric step means
 * the same relative lightness across scales.
 */

export const henna = {
  50: "#FBF0F1",
  100: "#F6DFE1",
  200: "#EABAC0",
  300: "#DA8D97",
  400: "#C2606E",
  500: "#A43D4E",
  600: "#7A2E3A",
  700: "#5F232C",
  800: "#481B22",
  900: "#331319",
  950: "#200C0F",
} as const;

export const marigold = {
  50: "#FDF6E9",
  100: "#FAEBC9",
  200: "#F3D48D",
  300: "#EBBB5C",
  400: "#DDA23A",
  500: "#C98A2C",
  600: "#A66E20",
  700: "#82551A",
  800: "#5F3D14",
  900: "#3D280D",
  950: "#251808",
} as const;

export const sand = {
  0: "#FFFFFF",
  50: "#FBF7F2",
  100: "#F5EEE6",
  200: "#E8DCD0",
  300: "#D6C4B3",
  400: "#B7A08A",
  500: "#8F7864",
  600: "#6B5847",
  700: "#4F4136",
  800: "#392F27",
  900: "#2B211D",
  950: "#1C1512",
} as const;

export const jade = { 100: "#E1F0EA", 500: "#2F6F5E", 700: "#1E4A3F" } as const;
export const terracotta = { 100: "#FBE2DC", 500: "#B3432B", 700: "#7A2D1D" } as const;
export const teal = { 100: "#E3EEF3", 500: "#3B6E8F", 700: "#284A5F" } as const;

export const colorPalette = { henna, marigold, sand, jade, terracotta, teal } as const;

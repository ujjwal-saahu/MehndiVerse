import { henna, jade, marigold, sand, teal, terracotta } from "./color-palette";

/**
 * Semantic color tokens — what components actually reference. Never point a
 * component at `colorPalette` directly; add a semantic name here instead, so
 * a future palette adjustment only touches this one mapping.
 */
export interface SemanticColors {
  background: string;
  surface: string;
  surfaceVariant: string;
  border: string;
  textPrimary: string;
  textSecondary: string;
  textOnPrimary: string;
  textOnAccent: string;
  primary: string;
  primaryHover: string;
  primaryPressed: string;
  accent: string;
  accentHover: string;
  success: string;
  successSurface: string;
  warning: string;
  warningSurface: string;
  danger: string;
  dangerSurface: string;
  info: string;
  infoSurface: string;
  focusRing: string;
}

export const lightColors: SemanticColors = {
  background: sand[50],
  surface: sand[0],
  surfaceVariant: sand[100],
  border: sand[200],
  textPrimary: sand[900],
  textSecondary: sand[600],
  textOnPrimary: sand[50],
  textOnAccent: sand[950],
  primary: henna[600],
  primaryHover: henna[700],
  primaryPressed: henna[800],
  accent: marigold[500],
  accentHover: marigold[600],
  success: jade[500],
  successSurface: jade[100],
  warning: marigold[500],
  warningSurface: marigold[100],
  danger: terracotta[500],
  dangerSurface: terracotta[100],
  info: teal[500],
  infoSurface: teal[100],
  focusRing: teal[500],
};

export const darkColors: SemanticColors = {
  background: sand[950],
  surface: "#241C18",
  surfaceVariant: sand[900],
  border: sand[800],
  textPrimary: sand[50],
  textSecondary: sand[300],
  textOnPrimary: sand[950],
  textOnAccent: sand[950],
  primary: henna[300],
  primaryHover: henna[200],
  primaryPressed: henna[100],
  accent: marigold[300],
  accentHover: marigold[200],
  success: jade[100],
  successSurface: jade[700],
  warning: marigold[300],
  warningSurface: marigold[700],
  danger: terracotta[100],
  dangerSurface: terracotta[700],
  info: teal[100],
  infoSurface: teal[700],
  focusRing: teal[100],
};

export const colors = { light: lightColors, dark: darkColors } as const;

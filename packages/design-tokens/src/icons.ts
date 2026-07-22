/** Icon sizes in px. `md` is the default inline-with-text size; `lg`/`xl` are
 * for standalone icon buttons and empty-state illustrations. */
export const iconSize = {
  xs: 16,
  sm: 20,
  md: 24,
  lg: 32,
  xl: 40,
} as const;

export type IconSizeKey = keyof typeof iconSize;

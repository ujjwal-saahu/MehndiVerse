/** Durations in ms. Premium/elegant motion favors measured, decelerating
 * transitions over bouncy/playful ones. */
export const duration = {
  instant: 0,
  fast: 120,
  base: 200,
  slow: 320,
  slower: 480,
} as const;

/** Cubic-bezier easing curves as CSS-ready strings; Flutter maps these to
 * `Curves` via apps/mobile/lib/core/theme/motion_tokens.dart. */
export const easing = {
  standard: "cubic-bezier(0.2, 0, 0, 1)",
  decelerate: "cubic-bezier(0, 0, 0, 1)",
  accelerate: "cubic-bezier(0.3, 0, 1, 1)",
  emphasized: "cubic-bezier(0.2, 0, 0, 1.1)",
} as const;

export const motion = { duration, easing } as const;

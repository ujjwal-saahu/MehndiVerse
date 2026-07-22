export * from "./breakpoints";
export * from "./color-palette";
export * from "./colors";
export * from "./icons";
export * from "./motion";
export * from "./radius";
export * from "./shadows";
export * from "./spacing";
export * from "./typography";

import { breakpoints } from "./breakpoints";
import { colorPalette } from "./color-palette";
import { colors } from "./colors";
import { iconSize } from "./icons";
import { motion } from "./motion";
import { radius } from "./radius";
import { shadows } from "./shadows";
import { spacing } from "./spacing";
import { typography } from "./typography";

/** The full token set as a single object, for consumers that want one
 * import (e.g. a Storybook-style docs page or a Flutter codegen script). */
export const tokens = {
  colorPalette,
  colors,
  typography,
  spacing,
  radius,
  shadows,
  motion,
  breakpoints,
  iconSize,
} as const;

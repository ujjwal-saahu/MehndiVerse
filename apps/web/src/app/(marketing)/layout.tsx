import type { ReactNode } from "react";

import { SiteShell } from "@/components/layout/site-shell";

export default async function MarketingLayout({ children }: { children: ReactNode }) {
  return <SiteShell>{children}</SiteShell>;
}

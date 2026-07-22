import type { ReactNode } from "react";

import { Footer } from "@/components/nav/footer";
import { PublicNav } from "@/components/nav/public-nav";

/** Responsive shell for public/marketing pages: header + main + footer.
 * Route-group layout for `(marketing)` — see src/app/(marketing)/layout.tsx.
 */
export async function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col">
      <PublicNav />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}

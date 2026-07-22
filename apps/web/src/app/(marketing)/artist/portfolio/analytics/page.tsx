import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { DesignCard } from "@/components/design-grid/design-card";
import { backendFetch } from "@/lib/backend";
import type { PortfolioAnalyticsData } from "@/lib/artist-directory-types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function PortfolioAnalyticsPage() {
  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const response = await backendFetch("/artist/portfolio/analytics", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (response.status === 404) {
    redirect("/artist/onboarding");
  }
  if (!response.ok) {
    redirect("/artist/portfolio");
  }
  const analytics = (await response.json()) as PortfolioAnalyticsData;

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Portfolio analytics</h1>
      <p className="mt-1 text-text-secondary">
        A high-level snapshot of your portfolio&apos;s reach. Detailed trends are coming in a future
        phase.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {[
          { label: "Designs", value: analytics.total_designs },
          { label: "Published", value: analytics.published_designs },
          { label: "Views", value: analytics.total_views },
          { label: "Likes", value: analytics.total_likes },
          { label: "Saves", value: analytics.total_saves },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-border bg-surface p-4">
            <p className="text-2xl font-semibold text-text-primary">
              {stat.value.toLocaleString()}
            </p>
            <p className="text-sm text-text-secondary">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          Top designs by views
        </h2>
        {analytics.top_designs.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">No designs yet.</p>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {analytics.top_designs.map((design) => (
              <DesignCard
                key={design.id}
                design={{
                  id: design.id,
                  title: design.title,
                  imageUrl: design.thumbnail_url,
                  href: `/artist/portfolio/${design.id}/edit`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

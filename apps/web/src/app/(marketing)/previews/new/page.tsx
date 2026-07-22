import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PreviewStudio } from "@/components/preview/preview-studio-lazy";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function NewPreviewPage() {
  const hasSession = (await cookies()).has(ACCESS_TOKEN_COOKIE);
  if (!hasSession) redirect("/login");

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        Hand &amp; foot design preview
      </h1>
      <p className="mt-2 text-text-secondary">
        Try a design on a photo before you book — no AR, just a design you can move, resize, rotate,
        and flip into place.
      </p>
      <div className="mt-6">
        <PreviewStudio />
      </div>
    </div>
  );
}

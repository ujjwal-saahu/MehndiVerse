import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PreviewStudio } from "@/components/preview/preview-studio-lazy";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session-cookies";

export default async function EditPreviewPage({ params }: { params: Promise<{ id: string }> }) {
  const hasSession = (await cookies()).has(ACCESS_TOKEN_COOKIE);
  if (!hasSession) redirect("/login");
  const { id } = await params;

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Edit preview</h1>
      <div className="mt-6">
        <PreviewStudio previewId={id} />
      </div>
    </div>
  );
}

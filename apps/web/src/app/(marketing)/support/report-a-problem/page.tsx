import { SupportRequestForm } from "@/components/support/support-request-form";

export const metadata = { title: "Report a problem | MehndiVerse" };

export default function ReportAProblemPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Report a problem</h1>
      <p className="text-text-secondary">
        Something not working right? Tell us what happened and we&apos;ll look into it. To report a
        specific design, comment, or user for a policy violation, use the &quot;Report&quot; action
        on that item instead — see our{" "}
        <a href="/legal/community-guidelines" className="text-primary hover:underline">
          Community Guidelines
        </a>
        .
      </p>
      <SupportRequestForm defaultCategory="bug_report" />
    </div>
  );
}

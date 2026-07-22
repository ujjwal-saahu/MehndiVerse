import { SupportRequestForm } from "@/components/support/support-request-form";

export const metadata = { title: "Contact support | MehndiVerse" };

export default function ContactSupportPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Contact support</h1>
      <p className="text-text-secondary">
        Questions about your account, a booking, or billing — send us a message and we&apos;ll reply
        by email. Found a bug instead?{" "}
        <a href="/support/report-a-problem" className="text-primary hover:underline">
          Report a problem
        </a>
        .
      </p>
      <SupportRequestForm defaultCategory="account_issue" />
    </div>
  );
}

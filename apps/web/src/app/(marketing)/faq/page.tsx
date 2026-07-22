const FAQS: { question: string; answer: string }[] = [
  {
    question: "How do I book an artist?",
    answer:
      'Find a design or artist you like, open their profile, and use "Request a booking." The artist can accept, decline, or send you a quote before anything is confirmed.',
  },
  {
    question: "How do refunds work?",
    answer:
      "Raise a refund request from your booking's detail page once it's marked completed. Staff review each request individually — see our Refund Policy.",
  },
  {
    question: "Can I cancel a booking?",
    answer:
      "Yes, from the booking detail page, any time before it's completed. See our Cancellation Policy for details.",
  },
  {
    question: "Are the AI-generated designs made by real artists?",
    answer:
      "No — every AI-generated design is clearly labeled as AI-generated, never attributed to a human artist. See our AI-Content Disclosure.",
  },
  {
    question: "How do I delete my account?",
    answer:
      'Go to Account → Privacy settings and choose "Delete account." Your account enters a grace period, after which your personal details are anonymized. Some records (completed payments, audit logs) are retained afterward for legal reasons.',
  },
  {
    question: "How do I get a copy of my data?",
    answer:
      "Go to Account → Data export to download a copy of your profile, bookings, payments, reviews, and consent history.",
  },
  {
    question: "How do I become a verified artist?",
    answer:
      "Sign up, then start artist onboarding from your account menu. You'll submit identity/business documents for staff review before you can publish paid services.",
  },
  {
    question: "Something's broken — how do I report it?",
    answer: 'Use "Report a problem" — it goes straight to a staff-reviewed queue.',
  },
];

export const metadata = { title: "FAQ | MehndiVerse" };

export default function FaqPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">
        Frequently asked questions
      </h1>
      <dl className="flex flex-col gap-6">
        {FAQS.map((faq) => (
          <div key={faq.question} className="flex flex-col gap-1">
            <dt className="font-display text-lg font-semibold text-text-primary">{faq.question}</dt>
            <dd className="text-text-secondary">{faq.answer}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-text-secondary">
        Didn&apos;t find your answer?{" "}
        <a href="/support/contact" className="text-primary hover:underline">
          Contact support
        </a>
        .
      </p>
    </div>
  );
}

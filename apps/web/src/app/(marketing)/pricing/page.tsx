import { PricingView } from "./pricing-view";

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Plans &amp; pricing</h1>
      <p className="mt-2 text-text-secondary">
        Upgrade for premium designs, more downloads, and higher AI-credit limits every month.
      </p>
      <PricingView />
    </div>
  );
}

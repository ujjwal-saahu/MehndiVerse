"use client";

import { useState } from "react";

import { SubmitButton } from "@/components/forms/submit-button";
import type { ArtistServiceData, PricingType } from "@/lib/artist-directory-types";
import { mutateJson } from "@/lib/gallery-client";

export function ServiceForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: ArtistServiceData;
  onSaved: (service: ArtistServiceData) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [pricingType, setPricingType] = useState<PricingType>(initial?.pricing_type ?? "fixed");
  const [priceAmount, setPriceAmount] = useState(initial?.price_amount?.toString() ?? "");
  const [priceMin, setPriceMin] = useState(initial?.price_min?.toString() ?? "");
  const [priceMax, setPriceMax] = useState(initial?.price_max?.toString() ?? "");
  const [currency, setCurrency] = useState(initial?.currency ?? "INR");
  const [durationMinutes, setDurationMinutes] = useState(
    initial?.duration_minutes?.toString() ?? "",
  );
  const [customerCapacity, setCustomerCapacity] = useState(
    initial?.customer_capacity?.toString() ?? "",
  );
  const [depositRequired, setDepositRequired] = useState(initial?.deposit_required ?? false);
  const [depositAmount, setDepositAmount] = useState(initial?.deposit_amount?.toString() ?? "");
  const [travelChargeAmount, setTravelChargeAmount] = useState(
    initial?.travel_charge_amount?.toString() ?? "",
  );
  const [cancellationPolicy, setCancellationPolicy] = useState(initial?.cancellation_policy ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || null,
        pricing_type: pricingType,
        price_amount: pricingType === "fixed" && priceAmount ? Number(priceAmount) : null,
        price_min: pricingType === "range" && priceMin ? Number(priceMin) : null,
        price_max: pricingType === "range" && priceMax ? Number(priceMax) : null,
        currency: currency.trim(),
        duration_minutes: durationMinutes ? Number(durationMinutes) : null,
        customer_capacity: customerCapacity ? Number(customerCapacity) : null,
        deposit_required: depositRequired,
        deposit_amount: depositRequired && depositAmount ? Number(depositAmount) : null,
        travel_charge_amount: travelChargeAmount ? Number(travelChargeAmount) : null,
        cancellation_policy: cancellationPolicy.trim() || null,
      };
      const saved = initial
        ? await mutateJson<ArtistServiceData>(
            `/api/artist/services/${initial.id}`,
            "PATCH",
            payload,
          )
        : await mutateJson<ArtistServiceData>("/api/artist/services", "POST", payload);
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-4"
    >
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">Service name</span>
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">Description</span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">Pricing</span>
        <select
          value={pricingType}
          onChange={(event) => setPricingType(event.target.value as PricingType)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        >
          <option value="fixed">Fixed price</option>
          <option value="range">Price range</option>
          <option value="custom_quote">Custom quote</option>
        </select>
      </label>

      <div className="flex gap-3">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Currency</span>
          <input
            type="text"
            value={currency}
            maxLength={3}
            onChange={(event) => setCurrency(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>
        {pricingType === "fixed" ? (
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-sm font-medium text-text-primary">Price</span>
            <input
              type="number"
              min={0}
              value={priceAmount}
              onChange={(event) => setPriceAmount(event.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
            />
          </label>
        ) : null}
        {pricingType === "range" ? (
          <>
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm font-medium text-text-primary">Min price</span>
              <input
                type="number"
                min={0}
                value={priceMin}
                onChange={(event) => setPriceMin(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1">
              <span className="text-sm font-medium text-text-primary">Max price</span>
              <input
                type="number"
                min={0}
                value={priceMax}
                onChange={(event) => setPriceMax(event.target.value)}
                className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
              />
            </label>
          </>
        ) : null}
      </div>

      <div className="flex gap-3">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Duration (minutes)</span>
          <input
            type="number"
            min={1}
            value={durationMinutes}
            onChange={(event) => setDurationMinutes(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Customer capacity</span>
          <input
            type="number"
            min={1}
            value={customerCapacity}
            onChange={(event) => setCustomerCapacity(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm text-text-primary">
        <input
          type="checkbox"
          checked={depositRequired}
          onChange={(event) => setDepositRequired(event.target.checked)}
        />
        Requires a deposit
      </label>
      {depositRequired ? (
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-text-primary">Deposit amount</span>
          <input
            type="number"
            min={0}
            value={depositAmount}
            onChange={(event) => setDepositAmount(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
          />
        </label>
      ) : null}

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">Travel charge (optional)</span>
        <input
          type="number"
          min={0}
          value={travelChargeAmount}
          onChange={(event) => setTravelChargeAmount(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">Cancellation policy</span>
        <textarea
          value={cancellationPolicy}
          onChange={(event) => setCancellationPolicy(event.target.value)}
          rows={2}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <div className="flex gap-3">
        <SubmitButton isSubmitting={isSaving} loadingLabel="Saving…">
          {initial ? "Save changes" : "Create service"}
        </SubmitButton>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

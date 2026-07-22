"use client";

import { useEffect, useState } from "react";

import { formatMinorAmount } from "@/lib/payment-types";
import type { PaymentData, PaymentOrderData, PaymentReceiptData } from "@/lib/payment-types";
import { loadRazorpayScript } from "@/lib/razorpay-checkout";

/** Which payment_type is available next, based on the booking's own status
 * — never a client choice, the server re-validates this too. See
 * docs/payments.md#4-server-side-amount-validation. */
function nextPaymentType(status: string): "deposit" | "full" | "balance" | null {
  if (status === "deposit_pending") return "deposit";
  if (status === "confirmed") return "full";
  if (status === "deposit_paid") return "balance";
  return null;
}

const PAYMENT_TYPE_LABELS: Record<string, string> = {
  deposit: "Pay deposit",
  full: "Pay in full",
  balance: "Pay remaining balance",
};

export function BookingPayments({
  bookingId,
  bookingStatus,
}: {
  bookingId: string;
  bookingStatus: string;
}) {
  const [payments, setPayments] = useState<PaymentData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [receipts, setReceipts] = useState<Record<string, PaymentReceiptData>>({});

  const load = async () => {
    const response = await fetch(`/api/bookings/${bookingId}/payments`);
    if (response.ok) setPayments(await response.json());
  };

  useEffect(() => {
    fetch(`/api/bookings/${bookingId}/payments`)
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (body) setPayments(body);
      });
  }, [bookingId]);

  // Polls our own backend (never trusts Razorpay's client-side callback) —
  // see docs/payments.md#4-never-trust-client-reported-success. Stops once
  // the payment reaches a terminal status or after a generous timeout.
  const pollUntilSettled = async (paymentId: string) => {
    for (let attempt = 0; attempt < 15; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const response = await fetch(`/api/bookings/${bookingId}/payments/${paymentId}`);
      if (response.ok) {
        const payment = (await response.json()) as PaymentData;
        if (payment.status !== "pending") {
          setAwaitingConfirmation(false);
          await load();
          return;
        }
      }
    }
    setAwaitingConfirmation(false);
    await load();
  };

  const pay = async () => {
    const paymentType = nextPaymentType(bookingStatus);
    if (!paymentType) return;
    setIsBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/bookings/${bookingId}/payments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payment_type: paymentType }),
      });
      const order = (await response.json()) as PaymentOrderData | { message: string };
      if (!response.ok) {
        setError((order as { message: string }).message);
        return;
      }
      const paymentOrder = order as PaymentOrderData;
      await loadRazorpayScript();
      const checkout = new window.Razorpay!({
        key: paymentOrder.provider_key_id,
        amount: paymentOrder.amount,
        currency: paymentOrder.currency,
        order_id: paymentOrder.provider_order_id,
        name: "MehndiVerse",
        description: `${paymentType} payment`,
        handler: () => {
          setAwaitingConfirmation(true);
          void pollUntilSettled(paymentOrder.payment_id);
        },
      });
      checkout.open();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the payment.");
    } finally {
      setIsBusy(false);
    }
  };

  const requestRefund = async (paymentId: string) => {
    const reason = window.prompt("Reason for the refund request (optional):") ?? undefined;
    setIsBusy(true);
    try {
      const response = await fetch(`/api/bookings/${bookingId}/payments/${paymentId}/refund`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      const body = await response.json();
      if (!response.ok) {
        setError(body.message);
        return;
      }
      await load();
    } finally {
      setIsBusy(false);
    }
  };

  const viewReceipt = async (paymentId: string) => {
    const response = await fetch(`/api/bookings/${bookingId}/payments/${paymentId}/receipt`);
    if (!response.ok) return;
    const receipt = (await response.json()) as PaymentReceiptData;
    setReceipts((current) => ({ ...current, [paymentId]: receipt }));
  };

  const nextType = nextPaymentType(bookingStatus);

  return (
    <section className="mt-8">
      <h2 className="font-medium text-text-primary">Payments</h2>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
      {awaitingConfirmation ? (
        <p className="mt-2 text-sm text-text-secondary">Waiting for the payment to be confirmed…</p>
      ) : null}

      {nextType ? (
        <button
          type="button"
          onClick={() => void pay()}
          disabled={isBusy}
          className="mt-3 rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary disabled:opacity-50"
        >
          {PAYMENT_TYPE_LABELS[nextType]}
        </button>
      ) : null}

      <ul className="mt-4 flex flex-col gap-2">
        {(payments ?? []).map((payment) => (
          <li key={payment.id} className="rounded-lg border border-border bg-surface p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-text-primary">
                {payment.payment_type} — {formatMinorAmount(payment.amount, payment.currency)}
              </span>
              <span className="text-xs text-text-secondary">{payment.status}</span>
            </div>
            {payment.failure_reason ? (
              <p className="mt-1 text-xs text-danger">{payment.failure_reason}</p>
            ) : null}
            <div className="mt-2 flex gap-3 text-xs">
              {payment.status === "succeeded" ? (
                <>
                  <button
                    type="button"
                    onClick={() => void viewReceipt(payment.id)}
                    className="text-primary hover:underline"
                  >
                    View receipt
                  </button>
                  <button
                    type="button"
                    onClick={() => void requestRefund(payment.id)}
                    disabled={isBusy}
                    className="text-primary hover:underline disabled:opacity-50"
                  >
                    Request refund
                  </button>
                </>
              ) : null}
            </div>
            {receipts[payment.id]
              ? (() => {
                  const receipt = receipts[payment.id];
                  if (!receipt) return null;
                  return (
                    <div className="mt-2 rounded-md bg-surface-variant p-2 text-xs text-text-secondary">
                      <p>Receipt — {receipt.provider_payment_id}</p>
                      <p>{receipt.artist_display_name}</p>
                      {receipt.service_name ? <p>{receipt.service_name}</p> : null}
                      <p>
                        {formatMinorAmount(receipt.amount, receipt.currency)}
                        {receipt.paid_at ? ` · ${new Date(receipt.paid_at).toLocaleString()}` : ""}
                      </p>
                    </div>
                  );
                })()
              : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

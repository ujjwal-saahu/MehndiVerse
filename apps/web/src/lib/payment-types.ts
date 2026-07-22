/** Shapes returned by the backend's payment endpoints (see
 * app/schemas/payment.py) — see docs/payments.md. Amounts are integer minor
 * currency units (paise, not rupees) — divide by 100 for display. */

export interface PaymentOrderData {
  payment_id: string;
  provider: string;
  provider_order_id: string;
  provider_key_id: string;
  amount: number;
  currency: string;
  status: string;
}

export interface PaymentData {
  id: string;
  booking_id: string;
  payer_id: string;
  amount: number;
  currency: string;
  provider: string;
  payment_type: "deposit" | "balance" | "full";
  status: "pending" | "succeeded" | "failed" | "refunded" | "partially_refunded";
  failure_reason: string | null;
  commission_amount: number | null;
  net_amount: number | null;
  paid_at: string | null;
  created_at: string;
}

export interface PaymentReceiptData {
  payment_id: string;
  booking_id: string;
  payment_type: string;
  amount: number;
  currency: string;
  status: string;
  paid_at: string | null;
  provider: string;
  provider_payment_id: string | null;
  artist_display_name: string | null;
  service_name: string | null;
}

export interface RefundData {
  id: string;
  payment_id: string;
  amount: number;
  currency: string;
  reason: string | null;
  status: "pending" | "approved" | "processed" | "rejected";
  requested_at: string;
  processed_at: string | null;
}

export function formatMinorAmount(amountMinor: number, currency: string): string {
  return `${currency} ${(amountMinor / 100).toFixed(2)}`;
}

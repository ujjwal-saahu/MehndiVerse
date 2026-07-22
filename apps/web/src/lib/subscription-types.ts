/** Shapes returned by the backend's subscription/coupon endpoints (see
 * app/schemas/subscription.py, app/schemas/coupon.py) — see
 * docs/subscriptions-and-entitlements.md. `price_amount`/`discount_amount`
 * are decimal major units (a human-facing list price), unlike
 * `payment-types.ts`'s integer-minor-unit `amount` fields — see
 * docs/payments.md#7-integer-minor-currency-units. */

export interface SubscriptionPlanData {
  id: string;
  name: string;
  slug: string;
  target_role: "customer" | "artist";
  price_amount: number;
  currency: string;
  billing_interval: "monthly" | "yearly";
  features: Record<string, unknown> | null;
  is_active: boolean;
}

export interface SubscriptionData {
  id: string;
  user_id: string;
  plan: SubscriptionPlanData;
  status: "active" | "cancelled" | "expired" | "past_due" | "trialing";
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  grace_period_ends_at: string | null;
  started_at: string;
  cancelled_at: string | null;
}

export interface MySubscriptionData {
  subscription: SubscriptionData | null;
  entitlements: Record<string, unknown>;
}

export interface SubscriptionStatusHistoryData {
  id: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
}

export interface CheckoutOrderData {
  payment_id: string;
  provider: string;
  provider_order_id: string;
  provider_key_id: string;
  amount: number;
  currency: string;
  status: string;
}

export interface BillingHistoryItemData {
  payment_id: string;
  plan_name: string | null;
  amount: number;
  currency: string;
  status: string;
  failure_reason: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface CouponValidateData {
  valid: boolean;
  message: string | null;
  discount_amount: number | null;
  final_amount: number | null;
}

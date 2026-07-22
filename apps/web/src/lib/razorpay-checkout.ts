"use client";

/** Shared Razorpay Checkout JS loader/types — used by both booking payments
 * and subscription checkout so `Window.Razorpay`'s global augmentation is
 * only declared once (a second, structurally-identical declaration
 * elsewhere is a TS2717 error, not a no-op). */

export interface RazorpayCheckoutOptions {
  key: string;
  amount: number;
  currency: string;
  order_id: string;
  name: string;
  description: string;
  handler: () => void;
  modal?: { ondismiss?: () => void };
}

export interface RazorpayCheckout {
  open: () => void;
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckout;
  }
}

const CHECKOUT_SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

export function loadRazorpayScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = CHECKOUT_SCRIPT_SRC;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load the payment checkout."));
    document.body.appendChild(script);
  });
}

# Prepaid credits

MarketingOS keeps prepaid billing off by default. A Stripe key copied from another project is **test mode only** and does not activate a customer checkout. Use a Stripe webhook signing secret created for this application's `/api/credits/webhook` endpoint. Never reuse another endpoint's webhook secret.

## Pricing and accounting

- One credit costs USD 0.01. Packages are fixed on the server: 1,000, 3,000 or 6,000 credits. The browser cannot set the payment amount or credited quantity.
- Each model call reserves enough credits **before** the provider request. A successful response is charged at twice its measured or conservatively estimated provider cost, rounded up to a whole credit. The unused reserve is returned to the account.
- Provider calls with unverified model prices, an unknown customer account, or insufficient credit are refused before any paid request. API transport retries are disabled in prepaid mode because an ambiguous failure may already have incurred a provider charge. Such failures keep the reserve for manual reconciliation; do not release it automatically.
- Anthropic web research is bounded to five searches and charged an upper-bound search surcharge. OpenAI web research is refused in prepaid mode until its full tool spend can be bounded. Research can require a large reserve because fetched pages are provider input; users may need a larger balance.
- Stripe events are signature checked. A checkout credits the account only after a matching recorded session is paid for the exact expected USD amount. Duplicate delivery is idempotent. A refund or dispute freezes further credit use and records the reversal for reconciliation, including when it arrives before the checkout event.
- The 2× processing markup does not by itself guarantee net profit: Stripe fees, taxes, infrastructure, failed calls and price changes also matter. Review the price table in `app/ai/models.py` and the hold bounds in `app/services/credit_meter.py` before enabling paid traffic. More than 30 days after the price review date in `app/core/config.py`, new model reservations and checkouts are refused. Account reads and signed Stripe webhooks remain available so customers and support can reconcile existing payments.
- A reservation is returned when local admission proves the provider request was never sent. A transport failure after sending, an unknown returned model or invalid measured cost retains the reservation for review. Do not infer an absence of provider charges from an error response.

## Activation

1. Apply migrations to a **backed-up** database. For a development database created by `init_db()` without Alembic history, use the existing migration reconciliation procedure in `docs/review-implementation.md`.
2. Use per-token provider API keys and set `AI_BILLING=api`, `AUTH_REQUIRED=true`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `PUBLIC_APP_URL`. Set `CREDIT_BILLING_ENABLED=true` only after checking the prices and keys. The subscription CLI is not suitable for charging a customer's measured usage.
3. Register `https://<your API host>/api/credits/webhook` in Stripe for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `charge.refunded`, and `charge.dispute.created`. Use the signing secret returned for **this endpoint**.
4. Verify a Stripe test purchase, duplicate webhook, delayed payment, refund and dispute end to end. Use a fresh production billing database for live credentials: startup refuses to mix test-funded and live-funded balances. Repeat a small live purchase before admitting customers.

Customer screens show credit balance and purchase history. Model names, provider prices and raw token counts are internal diagnostics. Support should reconcile held credits against the vendor's usage record after an uncertain transport failure.

Paid self-service is not qualified yet: a customer spending cap, reviewed provider-specific pricing, durable reconciliation tools and an end-to-end Stripe test remain required. See the [audit corrections and remaining launch blockers](audits/2026-10-07/corrections.md).

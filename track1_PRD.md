# Product Requirements Document
## Project: Agentic Trust Layer — Bounded, Gated AI Purchasing on Razorpay

**Version:** 1.0
**Owner:** [Your name]
**Target:** Razorpay Buildathon — Track 1 (AI Growth & Agentic Commerce)
**Backend:** FastAPI (Python)

---

## 1. Summary

Build a system that lets an AI agent purchase products on behalf of a user, end-to-end, but only within an explicit, deterministic, user-defined spending policy. The AI agent decides *what* to buy; a separate, non-LLM policy engine decides *whether* the purchase is allowed. Every action is logged to an inspectable audit trail. Payment execution runs on Razorpay's test-mode APIs.

**Core design law (must not be violated by any implementation):** The LLM never has authority to authorize or execute payment. It may only produce a purchase *proposal*. A deterministic policy engine is the sole authority that decides ALLOW or DENY. Razorpay is only called after an ALLOW decision.

---

## 2. Problem Statement

AI agents are increasingly able to act on a user's behalf, including making purchases. Existing agentic-commerce systems (Amazon Buy for Me, Visa Intelligent Commerce, Mastercard Agent Pay, Razorpay/NPCI's own UPI Reserve Pay pilot) solve "can an AI buy something," but the authorization/control logic in these systems is proprietary and not user-inspectable. There is no lightweight, generalizable, demonstrably-transparent control layer that a merchant could put in front of an AI buyer to bound what it's allowed to spend, on what, and for how long — and prove after the fact exactly why any transaction happened.

---

## 3. Goals

- **G1:** Demonstrate a merchant fully transactable by an AI buyer, end to end, using Razorpay test-mode APIs.
- **G2:** Demonstrate that every money-moving action is explainable, bounded, and gated by a deterministic (non-LLM) policy engine.
- **G3:** Provide a complete, queryable audit trail reconstructing every attempted and completed transaction.
- **G4:** Demonstrate at least one purchase attempt correctly denied, with a clear human-readable reason, with no Razorpay call made.
- **G5:** Ship a working demo runnable locally within the hackathon judging window.

### Non-goals
- Implementing or integrating with ACP, AP2, x402, or NPCI's UAP directly.
- Supporting real money movement (live mode).
- Multi-merchant marketplace support.
- Production-grade auth/security hardening (JWT/OAuth users, etc.) — a single-user hackathon demo is sufficient.
- Mobile app or non-web frontend.

---

## 4. Users & Primary User Story

**Primary user:** A person who wants to delegate a bounded amount of purchasing authority to an AI agent.

**User story:**
> As a user, I want to set explicit limits on what an AI shopping agent can spend — how much, at which merchant, in which category, and until when — so that I can let it make purchases on my behalf without giving it unrestricted access to my money.

**Acceptance criteria for the story:**
1. User can create a policy (amount cap, merchant, allowed categories, expiry) via a simple UI before interacting with the agent.
2. User can type a natural-language purchase request to the agent.
3. If the resulting proposal satisfies the policy, the purchase completes via Razorpay test-mode checkout and the user sees confirmation.
4. If the resulting proposal violates the policy, the user sees a clear denial reason and no payment is attempted.
5. User can view a full audit trail of every action taken, in order, with timestamps.

---

## 5. Functional Requirements

### FR1 — Merchant Catalog
- System exposes a catalog of 5–10 synthetic products.
- Each product has: `id`, `name`, `price` (paise), `category`, `merchant_id`.
- Endpoint: `GET /catalog` returns the full list.
- Endpoint: `GET /catalog/{id}` returns a single product.

### FR2 — Policy Management
- User can create exactly one **active** policy at a time via `POST /policy`.
- Policy fields: `max_amount` (paise), `merchant_id`, `allowed_categories` (list), `expires_at` (datetime), `require_confirmation_above` (optional, paise).
- Endpoint: `GET /policy/active` returns the currently active policy, or 404 if none.
- Creating a new policy deactivates any previous active policy (single active policy at a time — keep it simple).

### FR3 — Agent Intent Processing
- Endpoint: `POST /agent/intent` accepts `{ "text": "<natural language request>" }`.
- Internally: LLM is given the catalog + the user's text and must return a structured `Proposal` object (see §7 Data Model) — nothing else.
- The LLM call must NOT receive the active policy as context and must NOT be able to call the payment or policy modules directly. It is a pure proposal generator.
- If the LLM cannot find any reasonably matching product, return a proposal-generation failure (not a policy denial) with a clear message.

### FR4 — Policy Evaluation (the trust boundary)
- A pure, synchronous, dependency-free function `evaluate(proposal, policy) -> Decision` implements all checks:
  1. Policy not expired
  2. Proposal's merchant matches policy's merchant
  3. Proposal's category is in policy's allowed categories
  4. Proposal's amount ≤ policy's max_amount
  5. If proposal's amount > `require_confirmation_above` (when set), return DENY with `rule_triggered = "confirmation_required"`
- Must return a `Decision` object with `allowed: bool`, `reason: str`, `rule_triggered: str | None`.
- This function must have unit tests covering: 1 ALLOW case, and one DENY case per rule (5 deny cases minimum).
- This function must never call the LLM, the database, or Razorpay.

### FR5 — Payment Execution
- Only invoked when `Decision.allowed == True`.
- Creates a Razorpay Order via the Orders API (server-side, amount in paise, currency INR).
- Returns `order_id` to the frontend, which opens Razorpay Checkout (test mode) for the user to complete the mock payment.
- After checkout, payment status is confirmed either via webhook (`payment.captured`) or by polling `client.payment.fetch(payment_id)`.
- Endpoint: `POST /payments/execute` (creates the order, called only post-ALLOW).
- Endpoint: `POST /payments/webhook` (optional, if webhook approach is used).

### FR6 — Audit Trail
- Every state transition is written as an `AuditEvent`: intent received, proposal generated, policy evaluated (with full reason), payment order created, payment result (captured/failed).
- This must happen for BOTH allowed and denied flows — a denied flow still produces a complete, inspectable trail ending at the denial.
- Endpoint: `GET /audit` returns all events, ordered by timestamp ascending, each with `event_type`, `timestamp`, and a JSON payload of relevant details.

### FR7 — Frontend (minimal)
- Single page with three panels:
  1. **Policy form** — set max amount, merchant, categories, expiry.
  2. **Chat/intent box** — text input to send a purchase request, displays agent's response and outcome (allowed + Razorpay checkout embed, or denial + reason).
  3. **Live audit feed** — polls `GET /audit` and displays events in order, human-readably formatted.
- No authentication required. No styling requirements beyond basic clarity — this is a functional demo aid, not a polished product UI.

---

## 6. Non-Functional Requirements

- **NFR1 — Determinism of the policy engine:** Given the same `Proposal` and `Policy`, `evaluate()` must always return the same `Decision`. No randomness, no external calls.
- **NFR2 — Explainability:** Every `Decision` and every LLM `Proposal` must include a human-readable `reason` / `reasoning` string suitable for display to a non-technical user, not just an internal code.
- **NFR3 — Auditability:** The audit log is append-only within the scope of the demo (no update/delete endpoints needed).
- **NFR4 — Local runnability:** The entire system must run with `uvicorn app.main:app` plus a `.env` file of API keys, no external infra beyond Razorpay test mode and the chosen LLM API.
- **NFR5 — Amount correctness:** All monetary values are handled internally in paise (integers) to avoid floating-point errors; conversion to ₹ display format happens only at the presentation layer.

---

## 7. Data Model

```python
class Product(BaseModel):
    id: str
    name: str
    price: int              # paise
    category: str
    merchant_id: str

class Policy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    max_amount: int
    merchant_id: str
    allowed_categories: str      # comma-separated
    expires_at: datetime
    require_confirmation_above: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True

class Proposal(BaseModel):
    product_id: str
    product_name: str
    amount: int              # paise
    merchant_id: str
    category: str
    reasoning: str            # why the agent chose this product

class Decision(BaseModel):
    allowed: bool
    reason: str
    rule_triggered: str | None = None   # "expiry" | "merchant" | "category" | "amount" | "confirmation_required" | None

class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str           # "intent" | "proposal" | "policy_check" | "payment_created" | "payment_captured" | "payment_failed"
    payload: str               # JSON-encoded details
```

---

## 8. API Contract

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/catalog` | List products | none |
| GET | `/catalog/{id}` | Get one product | none |
| POST | `/policy` | Create/activate a policy | none |
| GET | `/policy/active` | Get current active policy | none |
| POST | `/agent/intent` | Submit natural-language purchase request | none |
| POST | `/payments/execute` | Create Razorpay order (internal, called post-ALLOW) | none |
| POST | `/payments/webhook` | Razorpay webhook receiver (optional) | Razorpay signature verify |
| GET | `/audit` | List all audit events | none |

*(No auth required — single-user hackathon demo scope. Note this explicitly as an out-of-scope simplification in the README.)*

---

## 9. End-to-End Flow (reference for implementation)

```
1. POST /policy               → policy created, active=true
2. POST /agent/intent {text}  → LLM generates Proposal → audit: "intent", "proposal"
3. evaluate(proposal, policy) → Decision                → audit: "policy_check"
4a. if allowed:
      POST /payments/execute  → Razorpay order created  → audit: "payment_created"
      user completes checkout → webhook/poll confirms   → audit: "payment_captured"
4b. if denied:
      response includes reason, rule_triggered
      no Razorpay call made
      flow ends at "policy_check" in audit trail
```

---

## 10. Milestones / Build Order

| # | Milestone | Definition of Done |
|---|---|---|
| M1 | Razorpay spike | Order created via SDK, test checkout completed, payment shows Captured in Razorpay dashboard |
| M2 | Catalog | `/catalog` returns seeded products |
| M3 | Policy engine | `evaluate()` implemented + passes all 6 unit tests (1 allow, 5 deny) |
| M4 | Policy API | `/policy` create + `/policy/active` working |
| M5 | Agent stub | `/agent/intent` returns a hardcoded Proposal (unblocks pipeline wiring) |
| M6 | Pipeline wiring | intent → proposal → policy engine → decision, fully connected |
| M7 | Payment wiring | ALLOW path creates real Razorpay order |
| M8 | Audit logging | Every step in M6/M7 writes an AuditEvent; `/audit` returns full trail |
| M9 | Real LLM | Swap stub for actual LLM call in `agent/llm.py` |
| M10 | Frontend | Policy form + intent box + live audit feed, functional |
| M11 | Full path testing | 3x successful happy-path runs; 1x each deny case verified in audit trail |
| M12 | Demo rehearsal | Timed 5-minute run-through matching Section 11 |

---

## 11. Demo Script (for validation, not implementation — include in README)

1. Set a policy live (max ₹2,000, one merchant, one category, expiry today+7d).
2. Submit intent: "buy me a birthday gift under ₹2,000" → show proposal → ALLOW → Razorpay checkout → captured, visible on Razorpay dashboard.
3. Submit intent that exceeds the cap → show DENY with exact reason → confirm no Razorpay order was created for this attempt.
4. Show the full audit trail, scrolled top to bottom.

---

## 12. Explicit Constraints for Implementation

- Do **not** let the LLM call any endpoint other than returning a `Proposal` JSON object.
- Do **not** pass the `Policy` object into the LLM prompt or context at any point.
- Do **not** call Razorpay before a `Decision.allowed == True` exists in the current request's flow.
- Do **not** skip writing an `AuditEvent` for a denied flow — denials must be as fully logged as approvals.
- Keep `policy/engine.py` free of any async code, DB session, or network call — it must be a pure function importable and testable in isolation.
- All monetary amounts in code are integers in paise; never use floats for money.

---

## 13. Open Questions to Resolve Before Coding

1. Which LLM provider/API key will be used for the agent module?
2. Webhook vs. polling for payment confirmation — decide based on whether a public URL (ngrok) will be available during the hackathon.
3. Single hardcoded merchant vs. `merchant_id` as a real field with multiple values in the catalog (recommend: keep to one merchant for MVP, field is present for extensibility only).

---

## 14. Definition of Done (project-level)

The project is complete when: a user can set a policy, submit a natural-language purchase request, see a completed real (test-mode) Razorpay payment for an allowed proposal, see a clean denial for a policy-violating proposal, and inspect a full audit trail explaining every step of both outcomes — all runnable locally end to end.

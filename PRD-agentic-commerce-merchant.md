# PRD: Agent-Transactable Merchant (Razorpay Agentic Commerce Track)

## 1. Overview

Build a fake e-commerce merchant ("Rohan's Sneaker Store") whose catalog and checkout are exposed as an **MCP (Model Context Protocol) server**, so that any MCP-compatible AI agent (e.g. Claude) can browse products and place a real order using Razorpay's test-mode APIs — with no merchant-specific code written into the buying agent.

This directly targets the hackathon track: *"make a merchant transactable by an AI buyer end to end."*

**Core idea:** the merchant speaks a standard, agent-readable protocol (catalog + checkout + status), inspired by ACP (product/checkout exposure) and AP2 (mandate/consent for spend authorization — deferred to v2).

## 2. Goals

- Prove a generic AI agent (not custom-built by us) can discover products and complete a real test-mode purchase using only our documented MCP tools.
- Keep every money-relevant action logged, explainable, and reviewable (the hackathon's "bar" requirement).
- Ship a working, demoable v1 first; layer in authorization/limits (mandate) in v2.

## 3. Non-Goals (v1)

- No mandate/consent token validation yet (deferred to v2).
- No max-orders-per-mandate enforcement yet (deferred to v2, depends on mandate).
- No webhook or automated payment-status polling yet — user tells Claude "paid" manually in v1.
- No scraping / auto-onboarding of real third-party merchant websites — catalog is seeded fake JSON.
- No fully in-chat/tokenized payment (RBI auth rules require redirect-based bank/UPI authentication; out of scope entirely).

## 4. Users / Actors

| Actor | Role |
|---|---|
| **Human shopper** | Chats with an AI buyer agent (e.g. Claude), completes payment via a redirect link |
| **AI buyer agent** | Any MCP-compatible agent (e.g. Claude Desktop/Claude.ai with our MCP server connected). Not built by us — this is the "generic agent" proof point |
| **Merchant MCP server** | What we build: exposes catalog + checkout + status as MCP tools, owns Razorpay integration, owns audit log |

## 5. Architecture

```
┌─────────────┐        MCP tool calls        ┌──────────────────────────┐
│   Claude     │ ───────────────────────────▶ │  Merchant MCP Server      │
│ (buyer agent)│ ◀─────────────────────────── │  (our backend)            │
└─────────────┘        tool responses         │                            │
      ▲                                       │  - search_catalog          │
      │ shows payment link                    │  - create_order            │
      │                                       │  - get_order_status        │
      ▼                                       │  - audit logger            │
┌─────────────┐                               │  - Razorpay client (test)  │
│ Human shopper│──── pays via redirect ───────▶│                            │
└─────────────┘        (Razorpay checkout)     └──────────────────────────┘
                                                        │
                                                        ▼
                                                ┌──────────────────────┐
                                                │  Live audit dashboard │
                                                │  (simple web page)    │
                                                └──────────────────────┘
```

Two independent processes: the merchant MCP server never talks to the human directly; the buyer agent never touches Razorpay directly. They only communicate via MCP tool calls.

## 6. MCP Tools Specification

### 6.1 `search_catalog`
Search/browse the merchant's product catalog.

**Input:**
```json
{
  "query": "string, optional — free text like 'black running shoes under 2500'",
  "max_price": "number, optional",
  "color": "string, optional",
  "size": "number, optional"
}
```

**Output:**
```json
{
  "products": [
    {
      "id": "sneaker_001",
      "name": "Air Runner Black",
      "price": 2199,
      "currency": "INR",
      "stock": 12,
      "attributes": { "color": "black", "sizes_available": [7, 8, 9, 10] }
    }
  ]
}
```

### 6.2 `create_order`
Place an order for a specific product.

**Input:**
```json
{
  "item_id": "sneaker_001",
  "size": 9,
  "qty": 1
}
```

**Output (success):**
```json
{
  "order_id": "order_abc123",
  "amount": 2199,
  "currency": "INR",
  "payment_url": "https://.../pay/order_abc123",
  "status": "pending_payment"
}
```

**Output (failure, e.g. out of stock):**
```json
{
  "error": "out_of_stock",
  "message": "Size 9 is currently unavailable for sneaker_001"
}
```

*Server-side logic:* validate item exists + stock available → create Razorpay order (test mode) → generate a hosted payment page/link → persist order as `pending_payment` → log the action.

### 6.3 `get_order_status`
Check status of a previously created order.

**Input:**
```json
{ "order_id": "order_abc123" }
```

**Output:**
```json
{
  "order_id": "order_abc123",
  "status": "pending_payment | paid | failed",
  "amount": 2199,
  "item": "Air Runner Black"
}
```

*v1 note:* status is only updated when the user manually confirms in chat and Claude (or the server, on a simple manual check) marks it paid — no webhook wired in v1. Structure the field now so v2 (webhook/polling) is a drop-in change, not a rewrite.

## 7. Data Model (minimal)

**Product** (`catalog.json`, seeded, ~10–15 items)
```json
{ "id", "name", "price", "currency", "stock", "attributes": { "color", "sizes_available" } }
```

**Order** (in-memory or lightweight DB, e.g. SQLite)
```json
{ "order_id", "item_id", "size", "qty", "amount", "status", "razorpay_order_id", "created_at" }
```

**Audit log entry** (append-only)
```json
{ "timestamp", "tool_name", "input", "decision", "reason", "result" }
```

## 8. Payment Flow (v1)

1. Buyer agent calls `search_catalog` → shows options to human.
2. Human picks one; buyer agent calls `create_order`.
3. Server creates Razorpay test-mode order, returns `payment_url`.
4. Buyer agent shows the link in chat; human opens it, completes payment via Razorpay's own hosted checkout page (redirect — required for bank/UPI authentication, not bypassable).
5. Human returns to chat, says "paid" / "done."
6. Buyer agent calls `get_order_status`; server reports current status (manually verified against Razorpay test dashboard for v1, or a simple manual-confirm step).
7. Buyer agent relays result to human.

**v2 upgrade path (not built now, but design should not block it):** Razorpay webhook → server updates order status automatically → resource updated without needing the "paid" manual trigger. Keep the order status field and update path abstracted behind one function so swapping manual-confirm for webhook-driven is a small change.

## 9. Explainability / Audit Requirement

- Every MCP tool call (`search_catalog`, `create_order`, `get_order_status`) appends one row to the audit log: timestamp, tool name, input, decision made, reason, result.
- A simple live dashboard (separate web page, not the chat) lists these rows in real time — this is the visible "show the audit trail" deliverable for judges.

## 10. Failure Handling Requirement

- v1 failure case: **out-of-stock item requested** → `create_order` returns a clear structured error (`error: "out_of_stock"`) rather than a crash or silent no-op; logged in the audit trail with reason.
- v2 (once mandate exists): over-mandate-limit request becomes the primary failure demo.

## 11. Tech Stack (finalized)

- **Backend framework:** FastAPI (Python) — hosts both the MCP server layer and any supporting HTTP endpoints (e.g. dashboard data, Razorpay redirect landing page).
- **MCP layer:** Python MCP SDK (`mcp` package), exposing `search_catalog`, `create_order`, `get_order_status` as tools. Can run as a stdio-based MCP server (for Claude Desktop) and/or wrapped for remote/HTTP MCP transport if needed for Claude.ai connectors.
- **Payments:** Razorpay Python SDK (`razorpay`), test-mode keys only.
- **Database:** SQLite (via `sqlmodel` or plain `sqlite3`/`aiosqlite`) — stores `products`, `orders`, `audit_log` tables. Lightweight, zero setup, sufficient for hackathon scope and easy to inspect directly during debugging/demo.
- **Catalog seed:** `catalog.json` loaded into the `products` table on startup (or read directly if you'd rather skip a products table and query JSON in-process — SQLite recommended once orders reference product IDs, for basic integrity).
- **Dashboard:** A FastAPI route serving a simple static HTML page + a `/audit-log` JSON endpoint it polls (`fetch` every 1–2s). WebSocket-based live push is a v2 stretch, not required for v1.
- **Buyer agent:** Claude Desktop or Claude.ai with the MCP server connected via local/remote MCP config — not custom-built by us.

### Project structure (finalized)
```
merchant-agent/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entrypoint; mounts api routes, static dashboard, starts MCP server
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py               # MCP tool definitions: search_catalog, create_order, get_order_status
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # HTTP routes: /audit-log (dashboard feed), /pay/{order_id} (Razorpay redirect landing)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── catalog_service.py      # search/filter logic over products table
│   │   ├── order_service.py        # create/validate orders, stock checks, status transitions
│   │   ├── payment_service.py      # wraps razorpay_client, builds payment_url, (v2) webhook handling
│   │   └── audit_service.py        # log_action() called from every MCP tool + relevant service calls
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product.py              # Product schema/table
│   │   ├── order.py                # Order schema/table
│   │   └── audit_log.py            # AuditLogEntry schema/table
│   │
│   ├── db.py                       # SQLite engine/session setup
│   ├── config.py                   # env var loading (Razorpay keys, DB path, mandate limits when added)
│   └── razorpay_client.py          # thin wrapper around Razorpay test-mode SDK calls
│
├── data/
│   └── catalog.json                # seed data loaded into products table on startup
│
├── static/
│   └── dashboard.html              # live audit log viewer, polls /audit-log
│
├── tests/
│   ├── test_catalog.py
│   ├── test_orders.py
│   └── test_mcp.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

**Build order note:** `models/` → `db.py` → `services/catalog_service.py` + `data/catalog.json` → `mcp/server.py` (`search_catalog` tool) → `razorpay_client.py` + `services/payment_service.py` → `services/order_service.py` → `mcp/server.py` (`create_order`, `get_order_status`) → `services/audit_service.py` wired into all three tools → `api/routes.py` + `static/dashboard.html`.

## 12. Milestones

| # | Milestone | Deliverable |
|---|---|---|
| 1 | Catalog seeded + `search_catalog` tool working | Claude can browse products via chat |
| 2 | `create_order` + Razorpay test-mode order creation | Real payment link generated from chat |
| 3 | Manual payment completion + `get_order_status` | End-to-end: browse → order → pay → confirm, live demo-able |
| 4 | Audit logging + dashboard | Every tool call visible on a live log page |
| 5 | Out-of-stock failure case | Demonstrated graceful rejection |
| 6 (v2) | Mandate token + max-orders-per-mandate | Authorization layer added |
| 7 (v2) | Webhook-based status update | Remove manual "paid" confirmation step |

## 14. HTTP API Routes (`app/api/routes.py`)

These are plain FastAPI HTTP routes — separate from the MCP tools in section 6. They exist for things a human (not the AI agent) interacts with directly: completing payment and viewing the audit dashboard.

| Method | Path | Goal | Description |
|---|---|---|---|
| `GET` | `/health` | Uptime check | Simple liveness check for local dev / demo sanity check before going on stage. Returns `{"status": "ok"}`. |
| `GET` | `/pay/{order_id}` | Human payment entry point | Renders a minimal HTML page for the given order (amount, item name) with a "Pay Now" button that launches Razorpay's hosted checkout (Checkout.js) using the `razorpay_order_id` stored against this order. This is the link `create_order` returns to the buyer agent. |
| `POST` | `/pay/{order_id}/verify` | Confirm a completed payment | Called by the client-side Razorpay Checkout success callback (from `/pay/{order_id}`'s page JS) with `razorpay_payment_id`, `razorpay_order_id`, `razorpay_signature`. Server verifies the signature using Razorpay's SDK, and if valid, updates the order status to `paid` in the DB and writes an audit log entry. This is what makes `get_order_status` return `paid` afterward — replaces a purely manual "trust the user's word" confirmation with an actually-verified one, at low extra cost. |
| `GET` | `/audit-log` | Feed the dashboard | Returns the full (or most recent N) audit log entries as JSON, ordered by timestamp. Polled by `dashboard.html` every 1–2 seconds to simulate a live feed in v1. |
| `GET` | `/dashboard` | Serve the demo UI | Serves `static/dashboard.html`, which polls `/audit-log` and renders each entry as a row (timestamp, tool/action, input, decision, reason, result). This is the page you leave open on a second screen/tab during the live demo. |
| `POST` | `/webhook/razorpay` *(v2, stub only in v1)* | Automated payment confirmation | Reserved endpoint for Razorpay's server-to-server webhook, so status updates don't depend on the client-side redirect completing (covers cases where the user closes the tab right after paying). Not required for v1 since `/pay/{order_id}/verify` already gives a real, verified confirmation path — but keep the route name reserved so v2 is additive, not a rename. |

**Design note on `/pay/{order_id}/verify` vs. the earlier "user just says paid in chat" plan:** since signature verification is a few lines of code with the Razorpay SDK you're already using, it's worth doing in v1 instead of pure manual trust — it costs little extra and means `get_order_status` reports a genuinely verified state rather than an assumed one, which is a stronger thing to say to judges. The buyer agent still surfaces it conversationally ("user says paid → agent calls `get_order_status` → sees `paid`, verified"), so the chat experience is unchanged; only the backend truth source is upgraded.

## 15. Acceptance Criteria for v1 Demo

- [ ] A generic Claude session (no custom prompting about "you are a shopping bot") connected to our MCP server can browse the catalog and describe products correctly.
- [ ] Claude can complete `create_order` and return a working Razorpay test-mode payment link.
- [ ] A real test-mode payment can be completed via that link.
- [ ] `get_order_status` reflects the correct state after payment.
- [ ] `/pay/{order_id}/verify` correctly verifies the Razorpay payment signature and only marks an order `paid` when verification succeeds.
- [ ] The audit dashboard shows every tool call made during the demo, with reasons.
- [ ] Requesting an out-of-stock item is rejected cleanly and logged, without crashing the server.

# AgentPay

**The transaction layer for agentic commerce.**

AI agents can already browse, recommend, and converse — but they can't safely spend money on a human's behalf. AgentPay closes that gap. It gives an AI agent a standard MCP interface for discovering products and completing real commerce transactions, while keeping **authorization, spending policy, human approval, payment execution, and auditability** fully under the merchant's control.

In short: **AgentPay makes a merchant transactable by an AI agent — without giving up control over how money moves.**

This project is a working demo merchant storefront built on AgentPay for the Razorpay AI/agentic commerce hackathon. It shows an AI agent (Claude) discovering products, creating an order, being checked against a spending policy, requesting human approval when needed, and completing a real Razorpay test-mode payment — all visible live on a dashboard.

## Demo

The demonstrated flow, end to end:

**Discover → Authorize → Order → Policy Check → Human Approval (if required) → Razorpay Payment → Verification → Live Audit**

1. The human generates an AgentPay authorization from the dashboard, scoped to the active MCP session.
2. Claude discovers products via MCP and creates an order.
3. AgentPay evaluates the order against the spending policy.
4. If the amount is above the approval threshold, Claude asks the human to explicitly approve before continuing.
5. Claude creates a Razorpay test-mode payment link and the human completes checkout.
6. AgentPay independently verifies the payment status against Razorpay.
7. Every step — authorization, policy decision, approval, payment, and status — is written to an append-only audit trail and shown live on the dashboard.

The dashboard gives a live view of authorization state, policy decisions, order state, payment status, and the full audit trail as the demo runs.

<!-- Add final demo video or dashboard screenshot here -->

## Architecture

```text
Claude / AI Agent
       │
       ▼
   AgentPay MCP
       │
       ▼
  Authorization
       │
       ▼
  Policy Engine
       │
       ▼
  Human Approval
       │
       ▼
      Order
       │
       ▼
     Razorpay
       │
       ▼
   Audit Log
       │
       ▼
  Live Dashboard
```

The AI agent never talks to Razorpay directly, and never bypasses policy or authorization — every transaction flows through AgentPay first.

## Key Features

- Agent authorization bound to the active MCP session
- Transaction policy engine with a maximum amount and an approval threshold
- Human-in-the-loop approval for transactions above the threshold
- Razorpay test-mode payments with independent payment verification
- Append-only, session-scoped audit trail
- MCP integration for Claude and other MCP-compatible agents
- Live AgentPay dashboard for authorization, policy, orders, payments, and audit events

## MCP Tools

AgentPay exposes its agent-facing interface as MCP tools. These are the only way the AI agent can interact with the merchant — there is no direct database or payment access from the agent side.

| Tool | Purpose |
|---|---|
| `get_agent_authorization` | Reads the authorization status and agent identity for the current MCP session. |
| `search_catalog` | Searches the merchant catalog by text, category, price, or attributes. |
| `create_order` | Creates an order for a product. Evaluates the transaction against AgentPay's policy and flags if approval is required. |
| `approve_transaction` | Approves an order that is awaiting human approval. Does not itself trigger payment. |
| `create_payment` | Creates a Razorpay test-mode payment link for an approved order. |
| `get_order_status` | Checks the current, Razorpay-verified payment status of an order. |

Every tool call is authorized against the active MCP session before it runs, and every policy-relevant decision is written to the audit trail.

## Policy: Spending Control

Every transaction is evaluated against a configurable policy before it can proceed to payment:

| Amount | Outcome |
|---|---|
| Up to ₹3,000 | Proceeds automatically |
| ₹3,000 – ₹5,000 | Requires explicit human approval before payment |
| Above ₹5,000 | Blocked — always, regardless of approval |

This is one of AgentPay's core differentiators: **approval can unlock a transaction under the threshold, but it can never override the maximum transaction limit.** An agent cannot talk, negotiate, or approve its way past the ceiling.

## Razorpay Integration

The integration uses **Razorpay test mode** end to end — no real money moves.

Payment flow: `create_order` → `create_payment` (creates a Razorpay test-mode payment link) → human completes the test payment → `get_order_status` independently verifies the result against Razorpay.

## Project Structure

```text
backend/
  app/
    main.py                 # FastAPI app, startup, router registration
    config.py                # Environment configuration
    db.py                    # SQLite and migrations
    razorpay_client.py       # Razorpay SDK client
    mcp/server.py             # MCP tools
    routes/                  # HTTP route groups
    models/                  # SQLModel tables
    services/                # Domain services
  data/catalog.json          # Seed catalog
  tests/                     # Unit, API, MCP, and payment tests
frontend/                    # AgentPay dashboard
razorpay_test/                # Manual Razorpay utilities
```

## Setup

From PowerShell at the repository root:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example backend\.env
```

Set the three test-mode values in `backend\.env`. Start FastAPI from the backend directory:

```powershell
Set-Location backend
..\env\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the dashboard at http://127.0.0.1:8000/.

## Claude MCP Configuration

Start the MCP server from the backend directory with:

```powershell
..\env\Scripts\python.exe -m app.mcp.server
```

For Claude Desktop, configure the MCP server using the absolute path to the repository's Python executable and `-m app.mcp.server`, with `backend` as the working directory. Do not put the AgentPay authorization token in Claude's configuration — generate it from the dashboard after the MCP server starts; it is bound to that MCP session.

## Testing

From `backend`:

```powershell
..\env\Scripts\python.exe -m pytest -q
```

The suite covers catalog and order behavior, authorization, policy decisions, human approval, MCP tools, payment services, Razorpay integration boundaries, and webhooks. Running the live Razorpay integration test requires valid Razorpay test credentials.

## Security & Trust Model

- **Session-bound authorization** — an agent's authorization is scoped to a single active MCP session.
- **Hashed authorization tokens** — tokens are never stored in plain text.
- **Policy enforcement before payment** — every order is evaluated against the spending policy before any payment can be created.
- **Human approval for transactions above the threshold** — the agent must obtain explicit approval before proceeding.
- **The maximum transaction limit cannot be bypassed** — no approval path exists above it.
- **Payment status is independently verified** against Razorpay rather than trusted from agent input.
- **Append-only audit trail** — authorization, policy, approval, and payment events are all recorded and visible on the dashboard.
- **Secrets stored in environment variables** — Razorpay test credentials are never hard-coded or committed.

## Known Limitations

This is a hackathon build, and scope was deliberately kept tight:

- Razorpay webhook signature verification is not yet enforced. Payment state is instead independently verified through Razorpay's payment-link status API, so order status shown to the agent and dashboard is always confirmed against Razorpay directly.
- The policy engine currently applies a single maximum amount and approval threshold per session, rather than more granular, per-category or per-merchant rules.
- The catalog is a small seeded demo dataset rather than a live product feed.

## Future Improvements

- Add Razorpay webhook signature verification as an additional, real-time confirmation path alongside status polling.
- Support richer, configurable policies (per-category limits, spending windows, multi-agent policies).
- Expand the catalog and support live merchant product feeds.
- Extend the dashboard with historical analytics across sessions.

See [PRD-agentic-commerce-merchant.md](PRD-agentic-commerce-merchant.md) for the original product specification.

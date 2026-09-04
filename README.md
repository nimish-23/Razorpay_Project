# AgentPay

The transaction layer for agentic commerce.

AgentPay gives an AI agent a standard MCP interface for discovering products and completing commerce transactions through authorization, policy checks, explicit human approval, Razorpay test payments, verified payment status, and a live audit dashboard.

## What it does

AI agent discovers products -> AgentPay authorization -> policy evaluation -> human approval when required -> Razorpay payment -> payment verification -> order and audit trail.

## Key Features

- Agent authorization bound to the active MCP session
- Transaction policy engine with amount limits and approval thresholds
- Human-in-the-loop approval for threshold transactions
- Razorpay test payments and payment verification
- Session-safe transactions and audit events
- MCP integration for Claude and other compatible agents
- Live AgentPay dashboard

## Architecture

```text
AI Agent / Claude
	|
	v
AgentPay MCP
	|
	v
Authorization
	|
	v
Policy Engine
	|
	v
Human Approval
	|
	v
Razorpay
	|
	v
Payment Verification
	|
	v
Order + Audit Trail
	|
	v
Live Dashboard
```

## Policy Example

The demo defaults are defined in `backend/app/services/policy_service.py`:

- INR 2,199 -> automatic
- INR 4,398 -> human approval
- INR 6,597 -> blocked

## Project Structure

```text
backend/
  app/
    main.py                 # FastAPI app, startup, router registration
    config.py               # Environment configuration
    db.py                   # SQLite and migrations
    razorpay_client.py      # Razorpay SDK client
    mcp/server.py           # MCP tools
    routes/                 # HTTP route groups
    models/                 # SQLModel tables
    services/               # Domain services
  data/catalog.json         # Seed catalog
  tests/                    # Unit, API, MCP, and payment tests
frontend/                   # AgentPay dashboard
razorpay_test/              # Manual Razorpay utilities
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

For Claude Desktop, configure the MCP server using the absolute path to the repository's Python executable and `-m app.mcp.server`, with `backend` as the working directory. Do not put the dynamic AgentPay authorization token in Claude configuration. Generate authorization from the dashboard after the MCP server starts; it is bound to that MCP session.

## Testing

From `backend`:

```powershell
..\env\Scripts\python.exe -m pytest -q
```

The suite covers catalog and order behavior, authorization, policy decisions, human approval, MCP tools, payment services, Razorpay integration boundaries, and webhooks. The live Razorpay integration test is marked separately; an obsolete live fixture may be skipped when its remote payment link no longer exists.

## Demo Flow

1. Start FastAPI and the MCP server.
2. Open the AgentPay dashboard and generate authorization.
3. Ask Claude to find black running shoes and select a product.
4. Place an order below the threshold, or explicitly approve a threshold transaction when Claude asks.
5. Have Claude call `create_payment`, then complete the Razorpay test checkout.
6. Ask Claude to check the order status and review the dashboard audit trail.

## Security Notes

- Use Razorpay test credentials only for this demo.
- Keep real values in `backend\.env`; never commit them.
- Authorization tokens are stored as hashes and are bound to the active MCP session.
- Payment completion depends on the existing Razorpay status verification flow.
- Transaction decisions, approval, payment, and order events are recorded in the session-scoped audit trail.

See [PRD-agentic-commerce-merchant.md](PRD-agentic-commerce-merchant.md) for the original product specification.
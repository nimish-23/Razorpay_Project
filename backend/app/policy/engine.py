from datetime import datetime, timezone
from app.models import Proposal, Policy, Decision


def evaluate(proposal: Proposal, policy: Policy) -> Decision:
    now = datetime.now(timezone.utc)
    expires_at = policy.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        return Decision(allowed=False, reason="Policy has expired", rule_triggered="expiry")

    if proposal.merchant_id != policy.merchant_id:
        return Decision(allowed=False, reason=f"Merchant '{proposal.merchant_id}' not authorized", rule_triggered="merchant")

    if proposal.category not in policy.categories_list():
        return Decision(allowed=False, reason=f"Category '{proposal.category}' not permitted", rule_triggered="category")

    if proposal.amount > policy.max_amount:
        return Decision(
            allowed=False,
            reason=f"Amount ₹{proposal.amount/100:.2f} exceeds limit ₹{policy.max_amount/100:.2f}",
            rule_triggered="amount",
        )

    if policy.require_confirmation_above is not None and proposal.amount > policy.require_confirmation_above:
        return Decision(allowed=False, reason="Requires manual confirmation", rule_triggered="confirmation_required")

    return Decision(allowed=True, reason="All policy checks passed")

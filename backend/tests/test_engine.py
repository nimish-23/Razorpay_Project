from sqlmodel import Session, select
from app.db import engine
from app.models import Policy, Proposal
from app.policy.engine import evaluate

def test_engine():
    print("=== Testing Policy Engine ===")
    
    with Session(engine) as session:
        # Fetch the active policy we created earlier
        policy = session.exec(select(Policy).where(Policy.active == True)).first()
        
        if not policy:
            print("No active policy found. Please run test_policy.py first to create one.")
            return

        print(f"\nActive Policy Loaded:")
        print(f"Max Amount: Rs.{policy.max_amount/100:.2f}")
        print(f"Merchant ID: {policy.merchant_id}")
        print(f"Categories: {policy.categories_list()}")
        print("-" * 40)

        # 1. ALLOW case (Valid proposal)
        prop_allow = Proposal(
            product_id="prod_005",
            product_name="Python Crash Course",
            amount=59900,
            merchant_id="merchant_001",
            category="books",
            reasoning="User likes python books"
        )
        print("\nTest 1: Valid Proposal (Rs.599.00, 'books', 'merchant_001')")
        decision1 = evaluate(prop_allow, policy)
        print(f"Allowed: {decision1.allowed} | Reason: {decision1.reason} | Rule: {decision1.rule_triggered}")

        # 2. DENY case (Amount exceeds limit)
        prop_deny_amount = Proposal(
            product_id="prod_010",
            product_name="Ergonomic Mouse",
            amount=299900,  # ₹2999, exceeds ₹2000
            merchant_id="merchant_001",
            category="electronics",
            reasoning="Really nice mouse"
        )
        print("\nTest 2: Exceeds Amount Limit (Rs.2999.00)")
        decision2 = evaluate(prop_deny_amount, policy)
        print(f"Allowed: {decision2.allowed} | Reason: {decision2.reason} | Rule: {decision2.rule_triggered}")

        # 3. DENY case (Category not allowed)
        prop_deny_cat = Proposal(
            product_id="prod_008",
            product_name="Desk Lamp",
            amount=119900,
            merchant_id="merchant_001",
            category="home",  # Not in 'books' or 'electronics'
            reasoning="Need light to read"
        )
        print("\nTest 3: Unapproved Category ('home')")
        decision3 = evaluate(prop_deny_cat, policy)
        print(f"Allowed: {decision3.allowed} | Reason: {decision3.reason} | Rule: {decision3.rule_triggered}")

if __name__ == "__main__":
    test_engine()

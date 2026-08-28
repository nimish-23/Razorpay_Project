from typing import List
from app.models import Product

CATALOG: List[Product] = [
    Product(
        id="prod_001",
        name="Wireless Earbuds",
        price=149900,
        category="electronics",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_002",
        name="Bluetooth Speaker",
        price=249900,
        category="electronics",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_003",
        name="USB-C Hub",
        price=89900,
        category="electronics",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_004",
        name="Mechanical Keyboard",
        price=599900,
        category="electronics",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_005",
        name="Python Crash Course",
        price=59900,
        category="books",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_006",
        name="Clean Code",
        price=44900,
        category="books",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_007",
        name="The Pragmatic Programmer",
        price=69900,
        category="books",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_008",
        name="Desk Lamp",
        price=119900,
        category="home",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_009",
        name="Ceramic Mug Set",
        price=79900,
        category="home",
        merchant_id="merchant_001"
    ),
    Product(
        id="prod_010",
        name="Ergonomic Mouse",
        price=299900,
        category="electronics",
        merchant_id="merchant_001"
    )
]

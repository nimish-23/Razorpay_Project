from sqlmodel import select

from app.db import get_session
from app.models.product import Product
from app.services.catalog_service import CatalogService


def test_get_all_products():
    with get_session() as session:
        products = session.exec(select(Product)).all()

        assert products is not None

        print("\n=== ALL PRODUCTS ===")

        for product in products:
            print(
                f"{product.id} | "
                f"{product.name} | "
                f"{product.category} | "
                f"₹{product.price}"
            )

        print(f"\nTotal products: {len(products)}")


def test_search_shoes():
    with get_session() as session:
        service = CatalogService(session)

        results = service.search_catalog(
            category="shoes"
        )

        print("\n=== SHOES ===")

        for product in results:
            print(
                f"{product.name} | "
                f"₹{product.price}"
            )

        print(f"Found: {len(results)}")

        for product in results:
            assert product.category.lower() == "shoes"


def test_search_black_products():
    with get_session() as session:
        service = CatalogService(session)

        results = service.search_catalog(
            attributes={
                "color": "black"
            }
        )

        print("\n=== BLACK PRODUCTS ===")

        for product in results:
            print(
                f"{product.name} | "
                f"{product.category} | "
                f"₹{product.price}"
            )

        print(f"Found: {len(results)}")

        for product in results:
            assert product.attributes.get("color", "").lower() == "black"


def test_combined_search():
    with get_session() as session:
        service = CatalogService(session)

        results = service.search_catalog(
            category="shoes",
            max_price=2500,
            attributes={
                "color": "black",
                "size": 9
            }
        )

        print("\n=== BLACK SHOES UNDER ₹2500, SIZE 9 ===")

        for product in results:
            print(
                f"{product.name} | "
                f"₹{product.price} | "
                f"Attributes: {product.attributes}"
            )

        print(f"Found: {len(results)}")

        for product in results:
            assert product.category.lower() == "shoes"
            assert product.price <= 2500
            assert product.attributes.get("color", "").lower() == "black"
            assert 9 in product.attributes.get("size", [])
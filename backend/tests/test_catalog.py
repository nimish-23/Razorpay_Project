from sqlmodel import select

from app.db import get_session
from app.models.product import Product
from app.services.catalog_service import CatalogService


def main():

    with get_session() as session:

        service = CatalogService(session)

        # Test 1: Get all products
        products = session.exec(
            select(Product)
        ).all()

        print("\n=== ALL PRODUCTS ===")

        for product in products:
            print(
                f"{product.id} | "
                f"{product.name} | "
                f"{product.category} | "
                f"₹{product.price}"
            )

        print(f"\nTotal products: {len(products)}")

        # Test 2: Search shoes
        print("\n=== SHOES ===")

        results = service.search_catalog(
            category="shoes"
        )

        for product in results:
            print(
                f"{product.name} | "
                f"₹{product.price}"
            )

        print(f"Found: {len(results)}")

        # Test 3: Black products
        print("\n=== BLACK PRODUCTS ===")

        results = service.search_catalog(
            color="black"
        )

        for product in results:
            print(
                f"{product.name} | "
                f"{product.category} | "
                f"₹{product.price}"
            )

        print(f"Found: {len(results)}")

        # Test 4: Combined search
        print("\n=== BLACK SHOES UNDER ₹2500, SIZE 9 ===")

        results = service.search_catalog(
            category="shoes",
            color="black",
            max_price=2500,
            size=9
        )

        for product in results:
            print(
                f"{product.name} | "
                f"₹{product.price} | "
                f"Sizes: {product.attributes.get('sizes_available', [])}"
            )

        print(f"Found: {len(results)}")


if __name__ == "__main__":
    main()
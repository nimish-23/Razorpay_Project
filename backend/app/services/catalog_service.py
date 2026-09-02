from typing import Optional
import json
from pathlib import Path

from sqlmodel import Session, select

from app.models.product import Product


class CatalogService:

    def __init__(self, session: Session):
        self.session = session

    # ---------------------------------------------------------
    # SEED CATALOG
    # ---------------------------------------------------------

    def seed_catalog(self, catalog_path: str):
        """
        Load products from catalog.json into the products table.

        Existing products are skipped based on their ID.
        """

        path = Path(catalog_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Catalog file not found: {path}"
            )

        with open(path, "r", encoding="utf-8") as file:
            products = json.load(file)

        added = 0
        skipped = 0

        for product_data in products:

            product_id = product_data["id"]

            # Check if product already exists
            existing_product = self.session.get(
                Product,
                product_id
            )

            if existing_product:
                skipped += 1
                continue

            # Create Product object
            product = Product(
                id=product_id,
                name=product_data["name"],
                category=product_data["category"],
                price=product_data["price"],
                currency=product_data.get("currency", "INR"),
                stock=product_data.get("stock", 0),
                attributes=product_data.get("attributes", {}),
            )

            self.session.add(product)

            added += 1

        self.session.commit()

        return {
            "total": len(products),
            "added": added,
            "skipped": skipped,
        }

    # ---------------------------------------------------------
    # GET PRODUCT
    # ---------------------------------------------------------

    def get_product(self, product_id: str):
        """
        Get a single product by its ID.
        """

        return self.session.get(
            Product,
            product_id
        )

    # ---------------------------------------------------------
    # SEARCH CATALOG
    # ---------------------------------------------------------

    def search_catalog(
        self,
        query: Optional[str] = None,
        max_price: Optional[float] = None,
        color: Optional[str] = None,
        category: Optional[str] = None,
        size: Optional[int] = None,
    ):
        """
        Search and filter products in the catalog.
        """

        statement = select(Product)

        products = self.session.exec(
            statement
        ).all()

        results = []

        for product in products:

            # ---------------------------------------------
            # TEXT SEARCH
            # ---------------------------------------------

            if query:

                search_text = query.lower().strip()

                if (
                    search_text not in product.name.lower()
                    and search_text not in product.category.lower()
                ):
                    continue

            # ---------------------------------------------
            # MAX PRICE
            # ---------------------------------------------

            if max_price is not None:

                if product.price > max_price:
                    continue

            # ---------------------------------------------
            # COLOR
            # ---------------------------------------------

            if color:

                product_color = product.attributes.get(
                    "color",
                    ""
                )

                if product_color.lower() != color.lower():
                    continue

            # ---------------------------------------------
            # CATEGORY
            # ---------------------------------------------

            if category:

                if product.category.lower() != category.lower():
                    continue

            # ---------------------------------------------
            # SIZE
            # ---------------------------------------------

            if size is not None:

                available_sizes = product.attributes.get(
                    "sizes_available",
                    []
                )

                if size not in available_sizes:
                    continue

            results.append(product)

        return results
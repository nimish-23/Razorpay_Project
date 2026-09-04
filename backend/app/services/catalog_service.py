from typing import Optional, Any
import json
import re
from pathlib import Path

from sqlmodel import Session, select

from app.models.product import Product
from app.services.audit_service import AuditService


class CatalogService:

    def __init__(
        self,
        session: Session,
        session_id: str = ""
    ):
        self.session = session
        self.audit_service = AuditService(
            session,
            session_id
        )

    def seed_catalog(self, catalog_path: str):
        path = Path(catalog_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Catalog file not found: {catalog_path}"
            )

        with open(path, "r", encoding="utf-8") as file:
            products = json.load(file)

        added = 0
        skipped = 0

        for product_data in products:

            existing_product = self.session.get(
                Product,
                product_data["id"]
            )

            if existing_product:
                skipped += 1
                continue

            product = Product(
                id=product_data["id"],
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
            "added": added,
            "skipped": skipped,
            "total": len(products),
        }

    def get_product(self, product_id: str):
        return self.session.get(Product, product_id)

    def search_catalog(
        self,
        query: Optional[str] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ):
        statement = select(Product)
        products = self.session.exec(statement).all()

        results = []

        for product in products:

            # Match every meaningful query token against the product's
            # searchable text, including attribute values.
            if query and not self._matches_query(product, query):
                continue

            # Price filter
            if max_price is not None:
                if product.price > max_price:
                    continue

            # Category filter
            if category:
                if product.category.lower() != category.lower():
                    continue

            # Generic attribute filtering
            if attributes:
                if not self._matches_attributes(
                    product.attributes or {},
                    attributes
                ):
                    continue

            results.append(product)

        returned_products = [
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "currency": product.currency,
                "stock": product.stock,
                "attributes": product.attributes,
            }
            for product in results
        ]

        self.audit_service.log_catalog_search(
            query=query,
            max_price=max_price,
            category=category,
            attributes=attributes,
            products=returned_products,
        )

        return results

    def _matches_query(self, product: Product, query: str) -> bool:
        query_tokens = self._normalized_tokens(query)
        searchable_values = [product.name, product.category]

        for value in (product.attributes or {}).values():
            if isinstance(value, list):
                searchable_values.extend(str(item) for item in value)
            else:
                searchable_values.append(str(value))

        searchable_tokens = {
            token
            for value in searchable_values
            for token in self._normalized_tokens(value)
        }
        return all(token in searchable_tokens for token in query_tokens)

    @staticmethod
    def _normalized_tokens(value: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9]+", value.lower())
        equivalents = {
            "running": "run",
            "runner": "run",
            "shoe": "shoe",
            "shoes": "shoe",
        }
        return {equivalents.get(token, token) for token in tokens}

    def _matches_attributes(
        self,
        product_attributes: dict[str, Any],
        requested_attributes: dict[str, Any],
    ) -> bool:

        for attribute_name, requested_value in requested_attributes.items():

            # Attribute does not exist
            if attribute_name not in product_attributes:
                return False

            available_value = product_attributes[attribute_name]

            # Product attribute is a list
            # Example:
            # "size": [7, 8, 9, 10]
            if isinstance(available_value, list):

                if requested_value not in available_value:
                    return False

            # Product attribute is a single value
            # Example:
            # "color": "black"
            # "battery_hours": 30
            # "noise_cancellation": true
            else:

                if requested_value != available_value:
                    return False

        return True
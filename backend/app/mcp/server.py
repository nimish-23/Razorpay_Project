from typing import Optional

from mcp.server.mcpserver import MCPServer

from app.db import get_session
from app.services.catalog_service import CatalogService


server = MCPServer(
    name="Rohan's Merchant",
    version="1.0.0",
)


@server.tool(
    name="search_catalog",
    description=(
        "Search products in the merchant catalog. "
        "You can filter by text, category, maximum price, color, or shoe size."
    ),
)
def search_catalog(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    color: Optional[str] = None,
    category: Optional[str] = None,
    size: Optional[int] = None,
) -> dict:
    """
    Search the merchant's product catalog.
    """

    with get_session() as session:
        catalog_service = CatalogService(session)

        products = catalog_service.search_catalog(
            query=query,
            max_price=max_price,
            color=color,
            category=category,
            size=size,
        )

        return {
            "count": len(products),
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "currency": product.currency,
                    "stock": product.stock,
                    "attributes": product.attributes,
                }
                for product in products
            ],
        }


if __name__ == "__main__":
    server.run("stdio")
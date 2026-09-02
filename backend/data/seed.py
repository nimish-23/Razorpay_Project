from pathlib import Path

from app.db import get_session
from app.services.catalog_service import CatalogService


CATALOG_PATH = Path(__file__).parent / "catalog.json"


def main():
    with get_session() as session:

        service = CatalogService(session)

        result = service.seed_catalog(
            str(CATALOG_PATH)
        )

        print("Catalog seeding complete!")
        print(f"Total products : {result['total']}")
        print(f"Added          : {result['added']}")
        print(f"Skipped        : {result['skipped']}")


if __name__ == "__main__":
    main()
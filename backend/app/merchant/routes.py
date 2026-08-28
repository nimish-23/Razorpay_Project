from fastapi import APIRouter, HTTPException
from typing import List
from app.models import Product
from app.merchant.data import CATALOG

router = APIRouter(prefix="/catalog", tags=["Catalog"])

@router.get("", response_model=List[Product])
def get_catalog():
    """Returns the full list of products."""
    return CATALOG

@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str):
    """Returns a single product by ID."""
    for p in CATALOG:
        if p.id == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")

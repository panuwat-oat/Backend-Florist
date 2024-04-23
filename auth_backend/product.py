from typing import Annotated
from fastapi import APIRouter, Depends, Form, Query
import requests

from main import User, get_current_active_user


router = APIRouter()


@router.get("/get_all_products")
async def get_all_products(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # request จาก products_backend
    response = requests.get("http://products_backend/get_all_products")
    return response.json()


# get_products_pagination
@router.get("/get_products_pagination")
async def get_products_pagination(
    current_user: Annotated[User, Depends(get_current_active_user)],
    catagory_id: int = Query(...),
    page: int = Query(1),
    limit: int = Query(10),
):
    # request จาก products_backend
    response = requests.get(
        "http://products_backend/get_products",
        params={"category_id": catagory_id, "page": page, "limit": limit},
    )
    return response.json()


@router.get("/add_product")
async def add_product(
    current_user: Annotated[User, Depends(get_current_active_user)],
    product_id: int = Form(...),
    category_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    product_image: str = Form(...),
):
    # request จาก products_backend
    response = requests.post(
        "http://products_backend/add_product",
        json={
            "product_id": product_id,
            "category_id": category_id,
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock_quantity,
            "product_image": product_image,
        },
    )
    return response.json()

from typing import Annotated
from fastapi import APIRouter, Depends, Form, Query
import requests

from main import User, get_current_active_user


router = APIRouter()


@router.post("/add_to_cart")
async def add_to_cart(
    current_user: Annotated[User, Depends(get_current_active_user)],
    product_id: int = Form(...),
    quantity: int = Form(...),
):
    cart = {
        "user_id": current_user.id,
        "items": [{"product_id": product_id, "quantity": quantity}],
    }
    response = requests.post("http://cart_backend/add_to_cart", json=cart)
    return response.json()


@router.get("/get_cart_pagination")
async def get_cart_pagination(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
    page: int = Query(1),
    limit: int = Query(10),
):
    response = requests.get(
        "http://cart_backend/get_cart_pagination",
        params={"user_id": user_id, "page": page, "limit": limit},
    )
    return response.json()

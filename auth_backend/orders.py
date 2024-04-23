from typing import Annotated
from fastapi import APIRouter, Depends, Form, Query
import requests

from main import User, get_current_active_user


router = APIRouter()


@router.post("/add_order")
async def add_order(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
    address_id: int = Query(...),
    order_date: str = Query(...),
    status: str = Query(...),
    total_price: float = Query(...),
    order_items: list = Query(...),
):
    order = {
        "user_id": user_id,
        "address_id": address_id,
        "order_date": order_date,
        "status": status,
        "total_price": total_price,
        "order_items": order_items,
    }
    response = requests.post("http://orders_backend/add_order", json=order)
    return response.json()


@router.get("/get_orders_all")
async def get_orders_all(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    response = requests.get("http://orders_backend/get_orders_all")
    return response.json()


@router.get("/get_order_by_user_id")
async def get_order_by_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
):
    response = requests.get(
        "http://orders_backend/get_order_by_user_id",
        params={"user_id": user_id},
    )
    return response.json()


@router.get("/get_order_by_user_id_and_status")
async def get_order_by_user_id_and_status(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
    status: str = Query(...),
):
    response = requests.get(
        "http://orders_backend/get_order_by_user_id_and_status",
        params={"user_id": user_id, "status": status},
    )
    return response.json()


@router.get("/edit_order_status")
async def edit_order_status(
    current_user: Annotated[User, Depends(get_current_active_user)],
    order_id: int = Query(...),
    status: str = Query(...),
):
    response = requests.put(
        "http://orders_backend/edit_order_status",
        params={"order_id": order_id, "status": status},
    )
    return response.json()



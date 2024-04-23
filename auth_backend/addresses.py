from typing import Annotated
from fastapi import APIRouter, Depends, Form, Query
import requests

from main import User, get_current_active_user


router = APIRouter()


@router.post("/add_address")
async def add_address(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    zip_code: str = Form(...),
    country: str = Form(...),
    is_current: bool = Form(...),
):

    address = {
        "user_id": user_id,
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": country,
        "is_current": is_current,
    }
    response = requests.post("http://addresses_backend/add_address", json=address)
    return response.json()


@router.get("/get_addresses_by_user_id")
async def get_addresses_by_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
):
    response = requests.get(
        "http://addresses_backend/get_addresses_by_user_id",
        params={"user_id": user_id},
    )
    return response.json()


@router.get("/get_current_address_by_user_id")
async def get_current_address_by_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: int = Query(...),
):
    response = requests.get(
        "http://addresses_backend/get_current_address_by_user_id",
        params={"user_id": user_id},
    )
    return response.json()


@router.put("/edit_address_by_address_id")
async def edit_address_by_address_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    address_id: int = Query(...),
    address: str = Query(...),
    city: str = Query(...),
    state: str = Query(...),
    zip_code: str = Query(...),
    country: str = Query(...),
    is_current: bool = Query(...),
):
    address = {
        "address_id": address_id,
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": country,
        "is_current": is_current,
    }
    response = requests.put(
        "http://addresses_backend/edit_address_by_address_id", json=address
    )
    return response.json()


@router.delete("/delete_address_by_address_id")
async def delete_address_by_address_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    address_id: int = Query(...),
):
    response = requests.delete(
        "http://addresses_backend/delete_address_by_address_id",
        params={"address_id": address_id},
    )
    return response.json()


@router.put("/set_current_address_by_address_id")
async def set_current_address_by_address_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    address_id: int = Query(...),
):
    response = requests.put(
        "http://addresses_backend/set_current_address_by_address_id",
        params={"address_id": address_id},
    )
    return response.json()

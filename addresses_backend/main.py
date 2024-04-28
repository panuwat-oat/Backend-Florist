
from typing import Annotated, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Header, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2,
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
import httpx
from pydantic import BaseModel
from fastapi import status
from jose import jwt, JWTError  # type: ignore
import requests

# import libraries เกี่ยวกับ mysql
import mysql.connector  # type: ignore


mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)


app = FastAPI(docs_url="/api/addresses/docs", openapi_url="/api/addresses/openapi.json")
from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenData(BaseModel):
    username: str | None = None


class Address(BaseModel):
    user_id: int
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    is_current: bool


class AddressResponse(BaseModel):
    address_id: int
    user_id: int
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    is_current: bool


SECRET_KEY = "florist"
ALGORITHM = "HS256"

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )
        token_data = TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return token_data


@app.post(
    "/api/addresses/add_address",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_address(address: Address, current_user: TokenData = Depends(get_current_user)):
    # เช็คว่า user_id นี้มีอยู่ในระบบหรือไม่ ถ้าไม่มีให้ return HTTPException 404
    # เช็คว่ามี address ที่เป็น current อยู่แล้วหรือไม่ ถ้ามีให้เปลี่ยนเป็นไม่ใช่
    # เพิ่ม address ใหม่เข้าไป
    mycursor = mydb.cursor()
    query = "SELECT * FROM users WHERE user_id=%s"
    mycursor.execute(query, (address.user_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="User not found")
    query = "SELECT * FROM addresses WHERE user_id=%s AND is_current=True"
    mycursor.execute(query, (address.user_id,))
    myresult = mycursor.fetchone()
    if myresult is not None:
        query = "UPDATE addresses SET is_current=False WHERE user_id=%s"
        mycursor.execute(query, (address.user_id,))
        mydb.commit()
    query = "INSERT INTO addresses (user_id, address, city, state, zip_code, country, is_current) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    mycursor.execute(
        query,
        (
            address.user_id,
            address.address,
            address.city,
            address.state,
            address.zip_code,
            address.country,
            address.is_current,
        ),
    )
    mydb.commit()
    return address


@app.get(
    "/api/addresses/get_addresses_by_user_id",
    response_model=List[AddressResponse],
)
def get_addresses_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):    
    # ดึงข้อมูล address ทั้งหมดของ user_id นี้ออกมา
    mycursor = mydb.cursor()
    query = "SELECT * FROM addresses WHERE user_id=%s"
    mycursor.execute(query, (user_id,))
    myresult = mycursor.fetchall()
    return myresult


@app.get(
    "/api/addresses/get_current_address_by_user_id", response_model=AddressResponse
    
)
def get_current_address_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    # ดึงข้อมูล address ที่เป็น current ของ user_id นี้ออกมา
    mycursor = mydb.cursor()
    query = "SELECT * FROM addresses WHERE user_id=%s AND is_current=True"
    mycursor.execute(query, (user_id,))
    myresult = mycursor.fetchone()
    return myresult


# แก้ไขข้อมูลที่อยู่ด้วย address_id
@app.put("/api/addresses/edit_address_by_address_id", response_model=AddressResponse)
def edit_address_by_address_id(
    address_id: int,
    address: Address,
    current_user: TokenData = Depends(get_current_user),
):
    # ตรวจสอบว่า address_id นี้มีอยู่ในระบบหรือไม่ ถ้าไม่มีให้ return HTTPException 404
    # ตรวจสอบว่า user_id ของ address_id นี้ตรงกับ user_id ที่ส่งมาหรือไม่ ถ้าไม่ตรงให้ return HTTPException 403
    # แก้ไขข้อมูล address ที่มี address_id นี้
    mycursor = mydb.cursor()
    query = "SELECT * FROM addresses WHERE address_id=%s"
    mycursor.execute(query, (address_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="Address not found")
    if myresult[1] != address.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    query = "UPDATE addresses SET address=%s, city=%s, state=%s, zip_code=%s, country=%s, is_current=%s WHERE address_id=%s"
    mycursor.execute(
        query,
        (
            address.address,
            address.city,
            address.state,
            address.zip_code,
            address.country,
            address.is_current,
            address_id,
        ),
    )
    mydb.commit()
    return address


# ลบข้อมูลที่อยู่ด้วย address_id
@app.delete(
    "/api/addresses/delete_address_by_address_id",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_address_by_address_id(
    address_id: int, current_user: TokenData = Depends(get_current_user)
):
    # ตรวจสอบว่า address_id นี้มีอยู่ในระบบหรือไม่ ถ้าไม่มีให้ return HTTPException 404
    # ลบข้อมูล address ที่มี address_id นี้
    mycursor = mydb.cursor()
    query = "SELECT * FROM addresses WHERE address_id=%s"
    mycursor.execute(query, (address_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="Address not found")
    query = "DELETE FROM addresses WHERE address_id=%s"
    mycursor.execute(query, (address_id,))
    mydb.commit()
    return {"message": "Deleted successfully"}


# ตั้งค่า address ที่เป็น current ด้วย address_id
@app.put(
    "/api/addresses/set_current_address_by_address_id", response_model=AddressResponse
)
def set_current_address_by_address_id(
    address_id: int, current_user: TokenData = Depends(get_current_user)
):
    # ตรวจสอบว่า address_id นี้มีอยู่ในระบบหรือไม่ ถ้าไม่มีให้ return HTTPException 404
    mycursor = mydb.cursor()
    query = "SELECT * FROM addresses WHERE address_id=%s"
    mycursor.execute(query, (address_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="Address not found")
    # ตรวจสอบว่ามี address ที่เป็น current อยู่แล้วหรือไม่ ถ้ามีให้เปลี่ยนเป็นไม่ใช่
    query = "UPDATE addresses SET is_current=False WHERE user_id=%s"
    mycursor.execute(query, (myresult[1],))
    mydb.commit()
    # ตั้งค่า address ที่เป็น current ด้วย address_id
    query = "UPDATE addresses SET is_current=True WHERE address_id=%s"
    mycursor.execute(query, (address_id,))
    mydb.commit()
    return myresult

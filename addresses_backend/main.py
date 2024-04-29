from typing import List
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import mysql.connector
from jose import jwt, JWTError  # type: ignore
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(docs_url="/api/addresses/docs", openapi_url="/api/addresses/openapi.json")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)
mycursor = mydb.cursor(dictionary=True)

SECRET_KEY = "florist"
ALGORITHM = "HS256"
security = HTTPBearer()


class TokenData(BaseModel):
    username: str | None = None


class Address(BaseModel):
    user_id: int
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    is_current: bool = True


class AddressResponse(BaseModel):
    address_id: int
    user_id: int
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    is_current: bool


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )
        return TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


@app.post("/api/addresses/add_address", response_model=AddressResponse, status_code=201)
def add_address(address: Address, current_user: TokenData = Depends(get_current_user)):
    mycursor.execute("SELECT * FROM users WHERE user_id = %s", (address.user_id,))
    if not mycursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    mycursor.execute(
        "SELECT * FROM addresses WHERE user_id = %s AND is_current = True",
        (address.user_id,),
    )
    if mycursor.fetchone():
        mycursor.execute(
            "UPDATE addresses SET is_current = False WHERE user_id = %s",
            (address.user_id,),
        )
    mycursor.execute(
        "INSERT INTO addresses (user_id, address, city, state, zip_code, country, is_current) VALUES (%s, %s, %s, %s, %s, %s, %s)",
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
    return AddressResponse(address_id=mycursor.lastrowid, **address.dict())


@app.get(
    "/api/addresses/get_addresses_by_user_id", response_model=List[AddressResponse]
)
def get_addresses_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute("SELECT * FROM addresses WHERE user_id = %s", (user_id,))
    return [AddressResponse(**address) for address in mycursor.fetchall()]


@app.get(
    "/api/addresses/get_current_address_by_user_id", response_model=AddressResponse
)
def get_current_address_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute(
        "SELECT * FROM addresses WHERE user_id = %s AND is_current = True", (user_id,)
    )
    address = mycursor.fetchone()
    if address is None:
        raise HTTPException(status_code=404, detail="No current address found")
    return AddressResponse(**address)


@app.put("/api/addresses/edit_address_by_address_id", response_model=AddressResponse)
def edit_address_by_address_id(
    address_id: int,
    address: Address,
    current_user: TokenData = Depends(get_current_user),
):
    mycursor.execute("SELECT * FROM addresses WHERE address_id = %s", (address_id,))
    existing_address = mycursor.fetchone()
    if not existing_address:
        raise HTTPException(status_code=404, detail="Address not found")
    mycursor.execute(
        "UPDATE addresses SET address = %s, city = %s, state = %s, zip_code = %s, country = %s WHERE address_id = %s",
        (
            address.address,
            address.city,
            address.state,
            address.zip_code,
            address.country,
            address_id,
        ),
    )
    mydb.commit()
    return AddressResponse(**{**existing_address, **address.dict()})


@app.delete("/api/addresses/delete_address_by_address_id", status_code=204)
def delete_address_by_address_id(
    address_id: int, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute("SELECT * FROM addresses WHERE address_id = %s", (address_id,))
    if not mycursor.fetchone():
        raise HTTPException(status_code=404, detail="Address not found")
    mycursor.execute("DELETE FROM addresses WHERE address_id = %s", (address_id,))
    mydb.commit()
    return {"message": "Deleted successfully"}


@app.put(
    "/api/addresses/set_current_address_by_address_id", response_model=AddressResponse
)
def set_current_address_by_address_id(
    address_id: int, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute("SELECT * FROM addresses WHERE address_id = %s", (address_id,))
    address = mycursor.fetchone()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    mycursor.execute(
        "UPDATE addresses SET is_current = False WHERE user_id = %s",
        (address["user_id"],),
    )
    mycursor.execute(
        "UPDATE addresses SET is_current = True WHERE address_id = %s", (address_id,)
    )
    mydb.commit()
    return AddressResponse(**address)

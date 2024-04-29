from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel
from fastapi import status


# import libraries เกี่ยวกับ mysql
import mysql.connector  # type: ignore


mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)

from jose import jwt, JWTError  # type: ignore


SECRET_KEY = "florist"
ALGORITHM = "HS256"

security = HTTPBearer()


class TokenData(BaseModel):
    username: str | None = None


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


app = FastAPI(docs_url="/api/cart/docs", openapi_url="/api/cart/openapi.json")

from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CartItem(BaseModel):
    quantity: int
    product_id: int


class Cart(BaseModel):
    user_id: int
    items: List[CartItem] = []


class Product(BaseModel):
    product_id: int
    category_id: int
    name: str
    description: str
    price: float
    product_image: str


class CartItemWithProduct(BaseModel):
    quantity: int
    product: Product


def get_product_details(product_id: int):
    mycursor = mydb.cursor(dictionary=True)
    query = "SELECT * FROM products WHERE product_id = %s"
    mycursor.execute(query, (product_id,))
    return mycursor.fetchone()


@app.post("/api/cart/add_to_cart", status_code=status.HTTP_201_CREATED)
def add_to_cart(cart: Cart, current_user: TokenData = Depends(get_current_user)):
    mycursor = mydb.cursor()
    # Ensure there is a cart for the user, get the cart_id
    query = "SELECT cart_id FROM cart WHERE user_id=%s"
    mycursor.execute(query, (cart.user_id,))
    cart_result = mycursor.fetchone()
    if not cart_result:
        query = "INSERT INTO cart (user_id) VALUES (%s)"
        mycursor.execute(query, (cart.user_id,))
        mydb.commit()
        cart_id = mycursor.lastrowid  # Get the new cart_id
    else:
        cart_id = cart_result[0]

    # Process each item in the cart
    for item in cart.items:
        query = "SELECT * FROM cart_items WHERE cart_id=%s AND product_id=%s"
        mycursor.execute(query, (cart_id, item.product_id))
        item_result = mycursor.fetchone()
        if not item_result:
            query = "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)"
            mycursor.execute(query, (cart_id, item.product_id, item.quantity))
        else:
            query = "UPDATE cart_items SET quantity = quantity + %s WHERE cart_id = %s AND product_id = %s"
            mycursor.execute(query, (item.quantity, cart_id, item.product_id))
        mydb.commit()

    return {"message": "Added to cart successfully"}


@app.get("/api/cart/get_cart_pagination", response_model=Dict[str, Any])
def get_cart(
    user_id: int = Query(
        ..., description="The ID of the user whose cart items are to be retrieved"
    ),
    page: int = Query(1, description="Page number of the pagination"),
    limit: int = Query(10, description="Number of items per page"),
    current_user: TokenData = Depends(get_current_user),
):
    mycursor = mydb.cursor(dictionary=True)
    offset = (page - 1) * limit
    query = """
    SELECT ci.quantity, p.product_id, p.category_id, p.name, 
           p.description, p.price, p.product_image
    FROM cart c
    JOIN cart_items ci ON c.cart_id = ci.cart_id
    JOIN products p ON ci.product_id = p.product_id
    WHERE c.user_id = %s LIMIT %s OFFSET %s
    """
    mycursor.execute(query, (user_id, limit, offset))
    items = mycursor.fetchall()

    cart_items_with_products = [
        {
            "quantity": item["quantity"],
            "product": {
                "product_id": item["product_id"],
                "category_id": item["category_id"],
                "name": item["name"],
                "description": item["description"],
                "price": item["price"],
                "product_image": item["product_image"],
            },
        }
        for item in items
    ]

    # Get total count of items in the cart for pagination
    query = """
    SELECT COUNT(*) as count
    FROM cart_items ci
    JOIN cart c ON ci.cart_id = c.cart_id
    WHERE c.user_id = %s
    """
    mycursor.execute(query, (user_id,))
    total_count = mycursor.fetchone()["count"]
    total_pages = (total_count + limit - 1) // limit  # Ceiling division

    return {
        "items": cart_items_with_products,
        "current_page": page,
        "total_pages": total_pages,
        "total_items": total_count,
        "limit": limit,
    }


@app.delete("/api/cart/delete_cart_item")
def delete_cart_item(
    user_id: int,
    product_id: int,
):
    mycursor = mydb.cursor()
    query = "DELETE FROM cart_items WHERE cart_id=%s AND product_id=%s"
    mycursor.execute(query, (user_id, product_id))
    mydb.commit()
    return {"message": "Deleted cart item successfully"}

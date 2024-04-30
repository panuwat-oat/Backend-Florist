from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import mysql.connector
from jose import jwt, JWTError

app = FastAPI(docs_url="/api/orders/docs", openapi_url="/api/orders/openapi.json")

# Database connection
mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)
mycursor = mydb.cursor(dictionary=True)

# Security setup
SECRET_KEY = "florist"
ALGORITHM = "HS256"
security = HTTPBearer()

# CORS Middleware setup
from fastapi.middleware.cors import CORSMiddleware
from fastapi import status

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data models
class TokenData(BaseModel):
    username: Optional[str]


class Product(BaseModel):
    product_id: int
    name: str
    price: float
    description: Optional[str] = None
    category_id: Optional[int] = None


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price_per_unit: float


class ProductDetails(BaseModel):
    name: str
    description: Optional[str]
    price: float
    category_id: Optional[int]
    product_image: Optional[str]


class OrderItemResponse(OrderItem):
    order_item_id: int
    product_details: ProductDetails


class Order(BaseModel):
    user_id: int
    address_id: int
    order_date: str
    status: str
    total_price: float
    order_items: List[OrderItem]


class OrderResponse(Order):
    order_id: int
    order_items: List[OrderItemResponse]


# Security dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )
        return TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


from datetime import datetime


def fetch_order_details(cursor, order_id):
    # Fetch order items with product details
    cursor.execute(
        """
        SELECT oi.order_item_id, oi.product_id, oi.quantity, oi.price_per_unit,
               p.name, p.description, p.price, p.category_id, p.product_image
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """,
        (order_id,),
    )
    items = cursor.fetchall()
    order_items = [
        OrderItemResponse(
            order_item_id=item["order_item_id"],
            product_id=item["product_id"],
            quantity=item["quantity"],
            price_per_unit=item["price_per_unit"],
            product_details=ProductDetails(
                name=item["name"],
                description=item["description"],
                price=item["price"],
                category_id=item["category_id"],
                product_image=item["product_image"],
            ),
        )
        for item in items
    ]

    # Fetch the order itself
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()

    return OrderResponse(
        order_id=order["order_id"],
        user_id=order["user_id"],
        address_id=order["address_id"],
        order_date=order["order_date"].strftime("%Y-%m-%d %H:%M:%S"),
        status=order["status"],
        total_price=float(order["total_price"]),
        order_items=order_items,
    )


# Endpoints
@app.post(
    "/api/orders/add_order",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_order(order: Order, current_user: TokenData = Depends(get_current_user)):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute(
        """
        INSERT INTO orders (user_id, address_id, order_date, status, total_price) VALUES (%s, %s, %s, %s, %s)
    """,
        (
            order.user_id,
            order.address_id,
            order.order_date,
            order.status,
            order.total_price,
        ),
    )
    order_id = cursor.lastrowid
    for item in order.order_items:
        cursor.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)
        """,
            (order_id, item.product_id, item.quantity, item.price_per_unit),
        )
    mydb.commit()
    return fetch_order_details(cursor, order_id)


@app.get("/api/orders/get_orders_all", response_model=List[OrderResponse])
def get_orders_all(current_user: TokenData = Depends(get_current_user)):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders")
    orders = [
        fetch_order_details(cursor, order["order_id"]) for order in cursor.fetchall()
    ]
    return orders


@app.get("/api/orders/get_order_by_user_id", response_model=List[OrderResponse])
def get_order_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user_id,))
    orders = [
        fetch_order_details(cursor, order["order_id"]) for order in cursor.fetchall()
    ]
    return orders


class OrderStatus(BaseModel):
    order_id: int
    status: str


@app.put("/api/orders/edit_order_status", response_model=OrderResponse)
def edit_order_status(
    order_status: OrderStatus, current_user: TokenData = Depends(get_current_user)
):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute(
        "UPDATE orders SET status = %s WHERE order_id = %s",
        (order_status.status, order_status.order_id),
    )
    mydb.commit()
    return fetch_order_details(cursor, order_status.order_id)

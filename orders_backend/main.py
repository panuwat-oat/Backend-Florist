from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi import status
import mysql.connector
from jose import jwt, JWTError

app = FastAPI(docs_url="/api/orders/docs", openapi_url="/api/orders/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    username: Optional[str]


class Product(BaseModel):
    product_id: int
    name: str
    price: float
    description: Optional[str]
    category_id: Optional[int]


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price_per_unit: float


class OrderItemResponse(OrderItem):
    order_item_id: int


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


@app.post(
    "/api/orders/add_order",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_order(order: Order, current_user: TokenData = Depends(get_current_user)):
    mycursor.execute(
        "INSERT INTO orders (user_id, address_id, order_date, status, total_price) VALUES (%s, %s, %s, %s, %s)",
        (
            order.user_id,
            order.address_id,
            order.order_date,
            order.status,
            order.total_price,
        ),
    )
    order_id = mycursor.lastrowid
    for item in order.order_items:
        mycursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)",
            (order_id, item.product_id, item.quantity, item.price_per_unit),
        )
    mydb.commit()
    return {**order.dict(), "order_id": order_id}


@app.get("/api/orders/get_orders_all", response_model=List[OrderResponse])
def get_orders_all(current_user: TokenData = Depends(get_current_user)):
    mycursor.execute("SELECT * FROM orders")
    orders = []
    for order in mycursor.fetchall():
        mycursor.execute(
            "SELECT * FROM order_items WHERE order_id=%s", (order["order_id"],)
        )
        order_items = [OrderItemResponse(**item) for item in mycursor.fetchall()]
        orders.append(OrderResponse(**order, order_items=order_items))
    return orders


@app.get("/api/orders/get_order_by_user_id", response_model=List[OrderResponse])
def get_order_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute("SELECT * FROM orders WHERE user_id=%s", (user_id,))
    orders = []
    for order in mycursor.fetchall():
        mycursor.execute(
            "SELECT * FROM order_items WHERE order_id=%s", (order["order_id"],)
        )
        order_items = [OrderItemResponse(**item) for item in mycursor.fetchall()]
        orders.append(OrderResponse(**order, order_items=order_items))
    return orders


@app.get(
    "/api/orders/get_order_by_user_id_and_status", response_model=List[OrderResponse]
)
def get_order_by_user_id_and_status(
    user_id: int, status: str, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute(
        "SELECT * FROM orders WHERE user_id=%s AND status=%s", (user_id, status)
    )
    orders = []
    for order in mycursor.fetchall():
        mycursor.execute(
            "SELECT * FROM order_items WHERE order_id=%s", (order["order_id"],)
        )
        order_items = [OrderItemResponse(**item) for item in mycursor.fetchall()]
        orders.append(OrderResponse(**order, order_items=order_items))
    return orders


@app.put("/api/orders/edit_order_status", response_model=OrderResponse)
def edit_order_status(
    order_id: int, status: str, current_user: TokenData = Depends(get_current_user)
):
    mycursor.execute(
        "UPDATE orders SET status=%s WHERE order_id=%s", (status, order_id)
    )
    mydb.commit()
    mycursor.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    order = mycursor.fetchone()
    mycursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    order_items = [OrderItemResponse(**item) for item in mycursor.fetchall()]
    return OrderResponse(**order, order_items=order_items)

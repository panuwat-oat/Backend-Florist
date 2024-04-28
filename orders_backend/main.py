from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi import status
import mysql.connector  # type: ignore
from jose import jwt, JWTError  # type: ignore

# Database Connection
mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)

# Security
SECRET_KEY = "florist"
ALGORITHM = "HS256"
security = HTTPBearer()

app = FastAPI(docs_url="/api/orders/docs", openapi_url="/api/orders/openapi.json")

# CORS Middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
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


# Dependencies
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


# Order Management Endpoints
@app.post(
    "/api/orders/add_order",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_order(order: Order, current_user: TokenData = Depends(get_current_user)):
    cursor = mydb.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, address_id, order_date, status, total_price) VALUES (%s, %s, %s, %s, %s)",
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
            "INSERT INTO order_items (order_id, product_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)",
            (order_id, item.product_id, item.quantity, item.price_per_unit),
        )
    mydb.commit()
    return {**order.dict(), "order_id": order_id}


# Helper function to fetch order details
def fetch_order_details(cursor):
    # Fetch the orders themselves
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    order_details = []
    for order in orders:
        cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order[0],))
        order_items = [
            OrderItemResponse(**dict(zip([col[0] for col in cursor.description], item)))
            for item in cursor.fetchall()
        ]
        order_details.append(
            OrderResponse(
                order_id=order[0],
                user_id=order[1],
                address_id=order[2],
                order_date=order[3].strftime("%Y-%m-%d %H:%M:%S"),
                status=order[4],
                total_price=float(order[5]),
                order_items=order_items,
            )
        )
    return order_details


# Main endpoint to get all orders with additional details
@app.get("/api/orders/get_orders_all", response_model=dict)
def get_orders_all(
    current_user: TokenData = Depends(get_current_user),
    page: int = Query(1),
    limit: int = Query(10),
):
    cursor = mydb.cursor()

    # Pagination for orders
    cursor.execute(
        "SELECT * FROM orders ORDER BY order_date DESC LIMIT %s OFFSET %s",
        (limit, (page - 1) * limit),
    )
    orders = fetch_order_details(cursor)

    # Statistics
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute(
        "SELECT DATE(order_date) as day, COUNT(*) FROM orders GROUP BY day ORDER BY day DESC"
    )
    orders_per_day = {row[0].strftime("%Y-%m-%d"): row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    orders_per_status = {row[0]: row[1] for row in cursor.fetchall()}

    # Compile everything into a single response object
    response = {
        "orders": orders,
        "total_orders": total_orders,
        "orders_per_day": orders_per_day,
        "orders_per_status": orders_per_status,
        "current_page": page,
        "total_pages": (total_orders + limit - 1) // limit,
        "limit": limit,
    }
    return response


def _get_order_details(order_id: int, cursor):
    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    order_items = cursor.fetchall()
    return {"order_id": order_id, "order_items": [dict(item) for item in order_items]}


@app.get("/api/orders/get_order_by_user_id", response_model=List[OrderResponse])
def get_order_by_user_id(
    user_id: int, current_user: TokenData = Depends(get_current_user)
):
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id=%s", (user_id,))
    orders = cursor.fetchall()
    return [_get_order_details(order[0], cursor) for order in orders]


@app.get(
    "/api/orders/get_order_by_user_id_and_status", response_model=List[OrderResponse]
)
def get_order_by_user_id_and_status(
    user_id: int, status: str, current_user: TokenData = Depends(get_current_user)
):
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE user_id=%s AND status=%s", (user_id, status)
    )
    orders = cursor.fetchall()
    return [_get_order_details(order[0], cursor) for order in orders]


@app.put("/api/orders/edit_order_status", response_model=OrderResponse)
def edit_order_status(
    order_id: int, status: str, current_user: TokenData = Depends(get_current_user)
):
    cursor = mydb.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE order_id=%s", (status, order_id))
    mydb.commit()
    return _get_order_details(order_id, cursor)

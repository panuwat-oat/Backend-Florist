from http.client import HTTPException
from typing import List, Optional
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from fastapi import status


# import libraries เกี่ยวกับ mysql
import mysql.connector  # type: ignore


mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI()

"""
CREATE TABLE `orders` (
    `order_id` int PRIMARY KEY AUTO_INCREMENT,
    `user_id` int,
    `address_id` int,
    `order_date` datetime,
    `status` varchar(255),
    `total_price` decimal
);

CREATE TABLE `order_items` (
    `order_item_id` int PRIMARY KEY AUTO_INCREMENT,
    `order_id` int,
    `product_id` int,
    `quantity` int,
    `price_per_unit` decimal
);
"""


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price_per_unit: float


class Order(BaseModel):
    user_id: int
    address_id: int
    order_date: str
    status: str
    total_price: float
    order_items: List[OrderItem]


class OrderItemResponse(BaseModel):
    order_item_id: int
    order_id: int
    product_id: int
    quantity: int
    price_per_unit: float


class OrderResponse(BaseModel):
    order_id: int
    user_id: int
    address_id: int
    order_date: str
    status: str
    total_price: float
    order_items: List[OrderItemResponse]


# สร้าง order ใหม่
@app.post(
    "/add_order", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
def add_order(order: Order):
    mycursor = mydb.cursor()
    sql = "INSERT INTO orders (user_id, address_id, order_date, status, total_price) VALUES (%s, %s, %s, %s, %s)"
    values = (
        order.user_id,
        order.address_id,
        order.order_date,
        order.status,
        order.total_price,
    )
    mycursor.execute(sql, values)
    mydb.commit()
    order_id = mycursor.lastrowid
    for order_item in order.order_items:
        sql = "INSERT INTO order_items (order_id, product_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)"
        values = (
            order_id,
            order_item.product_id,
            order_item.quantity,
            order_item.price_per_unit,
        )
        mycursor.execute(sql, values)
        mydb.commit()

    return order


# ดึง order ทั้งหมด
@app.get("/get_orders_all", response_model=List[OrderResponse])
def get_orders_all():
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM orders")
    myresult = mycursor.fetchall()
    orders = []
    for order in myresult:
        order_id = order[0]
        query = "SELECT * FROM order_items WHERE order_id=%s"
        mycursor.execute(query, (order_id,))
        order_items = mycursor.fetchall()
        order_items_list = []
        for order_item in order_items:
            order_item_id = order_item[0]
            order_id = order_item[1]
            product_id = order_item[2]
            quantity = order_item[3]
            price_per_unit = order_item[4]
            order_item = OrderItemResponse(
                order_item_id=order_item_id,
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
            )
            order_items_list.append(order_item)
        order_id = order[0]
        user_id = order[1]
        address_id = order[2]
        order_date = order[3]
        status = order[4]
        total_price = order[5]
        order = OrderResponse(
            order_id=order_id,
            user_id=user_id,
            address_id=address_id,
            order_date=order_date,
            status=status,
            total_price=total_price,
            order_items=order_items_list,
        )
        orders.append(order)
    return orders


# ดึง order ทั้งหมดของ user_id นี้
@app.get("/get_order_by_user_id", response_model=List[OrderResponse])
def get_order_by_user_id(user_id: int):
    mycursor = mydb.cursor()
    query = "SELECT * FROM orders WHERE user_id=%s"
    mycursor.execute(query, (user_id,))
    myresult = mycursor.fetchall()
    orders = []
    for order in myresult:
        order_id = order[0]
        query = "SELECT * FROM order_items WHERE order_id=%s"
        mycursor.execute(query, (order_id,))
        order_items = mycursor.fetchall()
        order_items_list = []
        for order_item in order_items:
            order_item_id = order_item[0]
            order_id = order_item[1]
            product_id = order_item[2]
            quantity = order_item[3]
            price_per_unit = order_item[4]
            order_item = OrderItemResponse(
                order_item_id=order_item_id,
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
            )
            order_items_list.append(order_item)
        order_id = order[0]
        user_id = order[1]
        address_id = order[2]
        order_date = order[3]
        status = order[4]
        total_price = order[5]
        order = OrderResponse(
            order_id=order_id,
            user_id=user_id,
            address_id=address_id,
            order_date=order_date,
            status=status,
            total_price=total_price,
            order_items=order_items_list,
        )
        orders.append(order)
    return orders


# ดึง order ทั้งหมดของ user_id นี้ที่มี status เป็น status
@app.get("/get_order_by_user_id_and_status", response_model=List[OrderResponse])
def get_order_by_user_id_and_status(user_id: int, status: str):
    mycursor = mydb.cursor()
    query = "SELECT * FROM orders WHERE user_id=%s AND status=%s"
    mycursor.execute(query, (user_id, status))
    myresult = mycursor.fetchall()
    orders = []
    for order in myresult:
        order_id = order[0]
        query = "SELECT * FROM order_items WHERE order_id=%s"
        mycursor.execute(query, (order_id,))
        order_items = mycursor.fetchall()
        order_items_list = []
        for order_item in order_items:
            order_item_id = order_item[0]
            order_id = order_item[1]
            product_id = order_item[2]
            quantity = order_item[3]
            price_per_unit = order_item[4]
            order_item = OrderItemResponse(
                order_item_id=order_item_id,
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
            )
            order_items_list.append(order_item)
        order_id = order[0]
        user_id = order[1]
        address_id = order[2]
        order_date = order[3]
        status = order[4]
        total_price = order[5]
        order = OrderResponse(
            order_id=order_id,
            user_id=user_id,
            address_id=address_id,
            order_date=order_date,
            status=status,
            total_price=total_price,
            order_items=order_items_list,
        )
        orders.append(order)
    return orders


# แก้ไข Status ของ order ที่ order_id นี้
@app.put("/edit_order_status", response_model=OrderResponse)
def edit_order_status(order_id: int, status: str):
    mycursor = mydb.cursor()
    query = "SELECT * FROM orders WHERE order_id=%s"
    mycursor.execute(query, (order_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="Order not found")
    query = "UPDATE orders SET status=%s WHERE order_id=%s"
    mycursor.execute(query, (status, order_id))
    mydb.commit()
    query = "SELECT * FROM order_items WHERE order_id=%s"
    mycursor.execute(query, (order_id,))
    order_items = mycursor.fetchall()
    order_items_list = []
    for order_item in order_items:
        order_item_id = order_item[0]
        order_id = order_item[1]
        product_id = order_item[2]
        quantity = order_item[3]
        price_per_unit = order_item[4]
        order_item = OrderItemResponse(
            order_item_id=order_item_id,
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
        )
        order_items_list.append(order_item)
    order_id = myresult[0]
    user_id = myresult[1]
    address_id = myresult[2]
    order_date = myresult[3]
    status = myresult[4]
    total_price = myresult[5]
    order = OrderResponse(
        order_id=order_id,
        user_id=user_id,
        address_id=address_id,
        order_date=order_date,
        status=status,
        total_price=total_price,
        order_items=order_items_list,
    )
    return order
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


class CartItem(BaseModel):
    product_id: int
    quantity: int


class Cart(BaseModel):
    user_id: int
    items: List[CartItem] = []


@app.post("/add_to_cart", status_code=status.HTTP_201_CREATED)
def add_to_cart(cart: Cart):
    # ตรวจสอบว่า user_id นี้มีอยู่ในระบบหรือไม่ และ มี cart อยู่แล้วหรือไม่ ถ้าไม่มีให้สร้างใหม่ ถ้ามีให้เช็คว่าสินค้าที่จะเพิ่มเข้าไปมีอยู่ใน cart อยู่แล้วหรือไม่ ถ้ามีให้เพิ่มจำนวนสินค้าเข้าไป ถ้าไม่มีให้เพิ่มสินค้าเข้าไปใหม่
    mycursor = mydb.cursor()
    query = "SELECT * FROM carts WHERE user_id=%s"
    mycursor.execute(query, (cart.user_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        query = "INSERT INTO carts (user_id) VALUES (%s)"
        mycursor.execute(query, (cart.user_id,))
        mydb.commit()
    for item in cart.items:
        query = "SELECT * FROM cart_items WHERE cart_id=%s AND product_id=%s"
        mycursor.execute(query, (cart.user_id, item.product_id))
        myresult = mycursor.fetchone()
        if myresult is None:
            query = "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)"
            mycursor.execute(query, (cart.user_id, item.product_id, item.quantity))
            mydb.commit()
        else:
            query = (
                "UPDATE cart_items SET quantity=%s WHERE cart_id=%s AND product_id=%s"
            )
            mycursor.execute(query, (item.quantity, cart.user_id, item.product_id))
            mydb.commit()
    return {"message": "Added to cart successfully"}


@app.get("/get_cart_pagination", response_model=List[CartItem])
def get_cart(user_id: int, page: int = 1, limit: int = 10):
    mycursor = mydb.cursor()
    query = "SELECT * FROM cart_items WHERE cart_id=%s"
    query += " LIMIT %s OFFSET %s"
    mycursor.execute(query, (user_id, limit, (page - 1) * limit))
    myresult = mycursor.fetchall()
    return myresult

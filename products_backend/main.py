from http.client import HTTPException
from typing import Annotated, List, Optional
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from fastapi import status


# import libraries เกี่ยวกับ mysql
from jose import JWTError, jwt
import mysql.connector  # type: ignore


mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)


app = FastAPI()


class ProductResponse(BaseModel):
    product_id: int
    category_id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    product_image: str


class Product(BaseModel):
    product_id: int
    category_id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    product_image: str


@app.get("/get_all_products", response_model=List[ProductResponse])
def get_all_products():
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM products")
    myresult = mycursor.fetchall()
    return myresult


@app.get("/get_products", response_model=List[ProductResponse])
def get_products(category_id: Optional[int] = None, page: int = 1, limit: int = 10):
    mycursor = mydb.cursor()
    query = "SELECT * FROM products"
    if category_id is not None:
        query += " WHERE category_id=%s"
        query += " LIMIT %s OFFSET %s"
        mycursor.execute(query, (category_id, limit, (page - 1) * limit))
    else:
        query += " LIMIT %s OFFSET %s"
        mycursor.execute(query, (limit, (page - 1) * limit))
    myresult = mycursor.fetchall()
    return myresult


# post new product with better error handling and status codes
@app.post("/add_product", status_code=status.HTTP_201_CREATED)
def add_product(product: Product):
    try:
        mycursor = mydb.cursor()
        sql = "INSERT INTO products (category_id, name, description, price, stock_quantity, product_image) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (
            product.category_id,
            product.name,
            product.description,
            product.price,
            product.stock_quantity,
            product.product_image,
        )
        mycursor.execute(sql, values)
        mydb.commit()
        return {"message": "Product added successfully"}
    except Exception as e:
        mydb.rollback()
        raise HTTPException(status_code=400, detail=str(e))

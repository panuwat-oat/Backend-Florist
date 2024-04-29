from typing import List, Optional
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    File,
    UploadFile,
    Form,
    Query,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from jose import jwt, JWTError
import shutil
import os
import requests

app = FastAPI(docs_url="/api/products/docs", openapi_url="/api/products/openapi.json")

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database connection setup
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="mysql", user="user", password="password", database="flowerstore"
        )
        return connection
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))


# JWT setup
SECRET_KEY = "florist"
ALGORITHM = "HS256"
security = HTTPBearer()


# Models
class TokenData(BaseModel):
    username: str | None = None


class Product(BaseModel):
    category_id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    product_image: str | None = None


class ProductResponse(Product):
    product_id: int
    category_name: str | None = None


class Category(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    category_id: int
    name: str


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


# Endpoints
@app.post(
    "/api/products/add_product",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product(product: Product, current_user: TokenData = Depends(get_current_user)):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO products (category_id, name, description, price, stock_quantity, product_image) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                product.category_id,
                product.name,
                product.description,
                product.price,
                product.stock_quantity,
                product.product_image,
            ),
        )
        connection.commit()
        product_id = cursor.lastrowid
        
        return {**product.dict(), "product_id": product_id}
    finally:
        cursor.close()
        connection.close()


@app.get("/api/products/get_products", response_model=List[ProductResponse])
def get_products(category_id: Optional[int] = None):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT p.*, c.name AS category_name FROM products p LEFT JOIN categories c ON p.category_id = c.category_id"
        if category_id:
            cursor.execute(query + " WHERE p.category_id = %s", (category_id,))
        else:
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


@app.post("/api/products/add_product_image")
def add_product_image(
    file: UploadFile = File(...),
    product_id: int = Form(...),
    current_user: TokenData = Depends(get_current_user),
):
    file_location = f"images/{product_id}.jpg"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE products SET product_image = %s WHERE product_id = %s",
            (f"api/products/images/{product_id}.jpg", product_id),
        )
        connection.commit()
        return {"message": "Image uploaded successfully", "file_path": file_location}
    finally:
        cursor.close()
        connection.close()


@app.get("/api/products/get_all_categories", response_model=List[CategoryResponse])
def get_all_categories():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM categories")
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


@app.post(
    "/api/products/add_category",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_category(
    category: Category, current_user: TokenData = Depends(get_current_user)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (%s)", (category.name,))
        connection.commit()
        category_id = cursor.lastrowid
        return {**category.dict(), "category_id": category_id}
    finally:
        cursor.close()
        connection.close()


@app.delete("/api/products/delete_category", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int, current_user: TokenData = Depends(get_current_user)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        connection.commit()
        return {"message": "Category deleted successfully"}
    finally:
        cursor.close()
        connection.close()


@app.get("/api/products/get_product_by_name", response_model=ProductResponse)
def get_product_by_name(
    product_name: str = Query(...),
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT p.*, c.name AS category_name FROM products p LEFT JOIN categories c ON p.category_id = c.category_id WHERE p.name = %s",
            (product_name,),
        )
        product = cursor.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    finally:
        cursor.close()
        connection.close()

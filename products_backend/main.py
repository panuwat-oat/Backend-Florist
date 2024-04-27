from http.client import HTTPException
from typing import Annotated, List, Optional
from fastapi import Depends, FastAPI, Query, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import status


# import libraries เกี่ยวกับ mysql
from jose import JWTError, jwt  # type: ignore
import mysql.connector  # type: ignore


mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)


app = FastAPI(docs_url="/api/products/docs", openapi_url="/api/products/openapi.json")

from jose import jwt, JWTError  # type: ignore


SECRET_KEY = "florist"
ALGORITHM = "HS256"

security = HTTPBearer()


# static files
@app.mount("/images", app=StaticFiles(directory="images"), name="images")

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


class ProductResponse(BaseModel):
    product_id: int
    category_id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    product_image: str


class Product(BaseModel):
    category_id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    product_image: str


@app.get("/api/products/get_all_products", response_model=List[ProductResponse])
def get_all_products(current_user: TokenData = Depends(get_current_user)):
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM products")
    myresult = mycursor.fetchall()
    return myresult


@app.get("/api/products/get_products", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[int] = None,
    page: int = 1,
    limit: int = 10,
    current_user: TokenData = Depends(get_current_user),
):
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
@app.post("/api/products/add_product", status_code=status.HTTP_201_CREATED)
def add_product(product: Product, current_user: TokenData = Depends(get_current_user)):
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


# add picture to product
@app.post("/api/products/add_product_image")
def add_product_image(
    file: bytes = Annotated[bytes, "file"],
    product_id: int = Annotated[int, "product_id"],
    current_user: TokenData = Depends(get_current_user),
):
    try:
        # อัพโหลดไฟล์ไปยัง server
        with open(f"images/{product_id}.jpg", "wb") as f:
            f.write(file)
        return {"message": "Image uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class Category(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    category_id: int
    name: str


@app.get("/api/products/get_all_categories")
def get_all_categories(current_user: TokenData = Depends(get_current_user)):
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM categories")
    myresult = mycursor.fetchall()
    return myresult


@app.post("/api/products/add_category")
def add_category(
    category: Category, current_user: TokenData = Depends(get_current_user)
):
    try:
        mycursor = mydb.cursor()
        sql = "INSERT INTO categories (name) VALUES (%s)"
        values = (category.name,)
        mycursor.execute(sql, values)
        mydb.commit()
        return {"message": "Category added successfully"}
    except Exception as e:
        mydb.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# delete category
@app.delete("/api/products/delete_category")
def delete_category(
    category_id: int = Query(...), current_user: TokenData = Depends(get_current_user)
):
    try:
        mycursor = mydb.cursor()
        sql = "DELETE FROM categories WHERE category_id = %s"
        mycursor.execute(sql, (category_id,))
        mydb.commit()
        return {"message": "Category deleted successfully"}
    except Exception as e:
        mydb.rollback()
        raise HTTPException(status_code=400, detail=str(e))

from fastapi import HTTPException
import shutil
from typing import Annotated, List, Optional
from fastapi import Depends, FastAPI, File, Form, Query, Security, UploadFile
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

from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from jose import jwt, JWTError  # type: ignore


SECRET_KEY = "florist"
ALGORITHM = "HS256"

security = HTTPBearer()

# เช็คว่ามี โฟลเดอร์ images หรือไม่ ถ้าไม่มีให้สร้างโฟลเดอร์ images
import os

if not os.path.exists("images"):
    os.makedirs("images")


app.mount(
    "/api/products/images",
    app=StaticFiles(directory="images"),
    name="images",
)


class TokenData(BaseModel):
    username: str | None = None


from jose import ExpiredSignatureError  # type: ignore


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
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return TokenData(username=username)


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


@app.get("/api/products/get_products")
def get_products(
    category_id: Optional[int] = None,
    page: int = 1,
    limit: int = 10,
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

    products = [
        {
            "product_id": product[0],
            "category_id": product[1],
            "name": product[2],
            "description": product[3],
            "price": product[4],
            "stock_quantity": product[5],
            "product_image": product[6],
        }
        for product in myresult
    ]

    # Get total count of items in the products table
    if category_id is not None:
        mycursor.execute(
            "SELECT COUNT(*) FROM products WHERE category_id=%s", (category_id,)
        )
    else:
        mycursor.execute("SELECT COUNT(*) FROM products")
    total_count = mycursor.fetchone()[0]
    total_pages = (total_count + limit - 1) // limit

    return {
        "items": products,
        "current_page": page,
        "total_pages": total_pages,
        "total_items": total_count,
        "limit": limit,
    }


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
        return {
            "message": "Product added successfully",
            "product_id": mycursor.lastrowid,
        }
    except Exception as e:
        mydb.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/products/add_product_image")
def add_product_image(
    file: UploadFile = File(...),
    product_id: int = Form(...),
    current_user: TokenData = Depends(get_current_user),
):
    try:
        # อัพโหลดไฟล์ไปยัง server
        # Note: You might want to add validation to check file content type, etc.
        file_location = f"images/{product_id}.jpg"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # อัพเดท product_image ในตาราง products
        mycursor = mydb.cursor()
        sql = "UPDATE products SET product_image = %s WHERE product_id = %s"
        file_location = f"api/products/images/{product_id}.jpg"
        values = (file_location, product_id)
        mycursor.execute(sql, values)
        mydb.commit()

        return {"message": "Image uploaded successfully", "file_path": file_location}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class Category(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    category_id: int
    name: str


@app.get("/api/products/get_all_categories", response_model=List[CategoryResponse])
def get_all_categories():
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM categories")
    myresult = mycursor.fetchall()
    # Convert tuple results to dictionary format expected by the Pydantic model
    categories = [
        {"category_id": category[0], "name": category[1]} for category in myresult
    ]
    return categories


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


import requests
import IPython


# get products description with text to speech
@app.get("/api/products/get_product_description_tts")
def get_product_description_tts(
    product_id: int = Query(...),
):
    mycursor = mydb.cursor()
    query = "SELECT description FROM products WHERE product_id = %s"
    mycursor.execute(query, (product_id,))
    myresult = mycursor.fetchone()
    if myresult is None:
        raise HTTPException(status_code=404, detail="Product not found")
    description = myresult[0]

    # Define the path for the audio file
    audio_file_path = f"images/product_{product_id}_audio.wav"

    # Check if the audio file already exists
    if os.path.exists(audio_file_path):
        return {"message": "Audio already generated", "file_path": audio_file_path}

    # API key for the text-to-speech service
    Apikey = "NMhdHNIpPJpc0nUKcn1asmqIPBqUuT9I"

    # Text-to-speech synthesis
    url = "https://api.aiforthai.in.th/vaja9/synth_audiovisual"
    headers = {"Apikey": Apikey, "Content-Type": "application/json"}
    data = {
        "input_text": description,
        "speaker": 1,
        "phrase_break": 0,
        "audiovisual": 0,
    }
    response = requests.post(url, json=data, headers=headers)

    # Check the response
    if response.status_code != 200 or "wav_url" not in response.json():
        raise HTTPException(status_code=500, detail="Failed to generate audio")

    # Download the audio file
    audio_url = response.json()["wav_url"]
    resp = requests.get(audio_url, headers={"Apikey": Apikey})
    if resp.status_code == 200:
        with open(audio_file_path, "wb") as f:
            f.write(resp.content)
        return {"message": "Audio generated successfully", "file_path": audio_file_path}
    else:
        raise HTTPException(status_code=500, detail="Failed to download audio")

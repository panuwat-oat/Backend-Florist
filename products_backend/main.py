from typing import List, Optional
import IPython
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
from fastapi.staticfiles import StaticFiles
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


app.mount("/api/products/images", app=StaticFiles(directory="images"), name="images")


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


@app.get("/api/products/get_products", response_model=dict)
def get_products(
    category_id: Optional[int] = Query(None),
    page: int = Query(1),
    limit: int = Query(10),
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query_base = """
        SELECT p.product_id, p.category_id, c.name AS category_name, p.name, p.description, 
               p.price, p.stock_quantity, p.product_image
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        """
        if category_id:
            query_base += " WHERE p.category_id = %s"

        # Prepare the query for pagination
        query_pagination = query_base + " LIMIT %s OFFSET %s"
        offset = (page - 1) * limit
        if category_id:
            cursor.execute(query_pagination, (category_id, limit, offset))
        else:
            cursor.execute(query_pagination, (limit, offset))

        products = cursor.fetchall()

        # Calculate total items and pages
        if category_id:
            cursor.execute(
                "SELECT COUNT(*) FROM products WHERE category_id = %s", (category_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM products")

        total_items = cursor.fetchone()["COUNT(*)"]
        total_pages = (
            total_items + limit - 1
        ) // limit  # This calculates the ceiling of the division

        return {
            "items": products,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
        }
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


# get products description with text to speech
@app.get("/api/products/get_product_description_tts")
def get_product_description_tts(
    product_id: int = Query(...),
):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT description FROM products WHERE product_id = %s", (product_id,)
    )
    myresult = cursor.fetchone()

    if myresult is None:
        raise HTTPException(status_code=404, detail="Product not found")
    description = myresult[0]

    # Define the path for the audio file
    audio_file_path = f"images/product_{product_id}_audio.wav"

    # Check if the audio file already exists
    if os.path.exists(audio_file_path):
        return {"message": "Audio already generated", "file_path": audio_file_path}

    # ระบุ api key

    Apikey = "NMhdHNIpPJpc0nUKcn1asmqIPBqUuT9I"

    # สังเคราะห์เสียง
    url = "https://api.aiforthai.in.th/vaja9/synth_audiovisual"
    headers = {"Apikey": Apikey, "Content-Type": "application/json"}
    text = description
    data = {"input_text": text, "speaker": 1, "phrase_break": 0, "audiovisual": 0}
    response = requests.post(url, json=data, headers=headers)
    print(response.json())

    # ดาวน์โหลดไฟล์เสียง
    resp = requests.get(response.json()["wav_url"], headers={"Apikey": Apikey})
    if resp.status_code == 200:
        with open(audio_file_path, "wb") as f:
            f.write(resp.content)
        return {
            "message": "Audio generated successfully",
            "file_path": f"api/products/{audio_file_path}",
        }
    else:
        return {
            "message": "Failed to generate audio",
            "message_form_api": resp.json(),
            "reason": resp.reason,
        }

from datetime import datetime, timedelta, timezone
from typing import Annotated


from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext
from pydantic import BaseModel


import requests

# import libraries เกี่ยวกับ mysql
import mysql.connector  # type: ignore


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "florist"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

mydb = mysql.connector.connect(
    host="mysql", user="user", password="password", database="flowerstore"
)


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    user_id: int
    password_hash: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(openapi_url="/api/auth/openapi.json", docs_url="/api/auth/docs")

from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_password(plain_password, password_hash):
    return pwd_context.verify(plain_password, password_hash)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    myresult = mycursor.fetchall()
    if myresult:
        user = myresult[0]
        user = dict(zip(mycursor.column_names, user))
        return UserInDB(**user)


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/api/auth/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    print(user.user_id)
    return Token(access_token=access_token, token_type="bearer", user_id=user.user_id)


class User_Register(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    phone_number: str


@app.post("/api/auth/register", tags=["Auth"])
async def register_user(user: User_Register):
    mycursor = mydb.cursor()
    sql = "INSERT INTO users (username, email, first_name, last_name, phone_number, created_at, updated_at, role, password_hash, disabled) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (
        user.username,
        user.email,
        user.first_name,
        user.last_name,
        user.phone_number,
        datetime.now(),
        datetime.now(),
        "user",
        get_password_hash(user.password),
        False,
    )
    mycursor.execute(sql, val)
    mydb.commit()
    return {"message": "User created successfully"}


@app.get("/api/auth/me", tags=["Auth"])
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

SECRET_KEY = "safedrive-rj-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: int
    full_name: str
    email: str

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": user.email})
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    hashed_pwd = hash_password(user.password)
    
    db.execute(text("""
        INSERT INTO users (full_name, email, password_hash)
        VALUES (:name, :email, :password)
    """), {
        "name": user.full_name,
        "email": user.email,
        "password": hashed_pwd
    })
    
    db.commit()
    return {"message": "Usuário criado com sucesso"}

@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT id, email, password_hash, full_name
        FROM users WHERE email = :email
    """), {"email": credentials.username})
    
    user = result.fetchone()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )
    
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        result = db.execute(text("""
            SELECT id, full_name, email
            FROM users WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return {"id": user.id, "full_name": user.full_name, "email": user.email}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

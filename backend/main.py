import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional, List, Any

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://frontend-mu-ten-95.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./inventory.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    supplier = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

class ProductCreate(BaseModel):
    name: str
    quantity: float
    threshold: float
    supplier: Optional[str] = ""

class ProductUpdate(BaseModel):
    quantity: float

@app.get("/products")
def get_products():
    db = SessionLocal()
    products = db.query(Product).all()
    db.close()
    return [
        {
            "id": p.id,
            "name": p.name,
            "quantity": p.quantity,
            "threshold": p.threshold,
            "supplier": p.supplier,
            "reorder_needed": p.quantity < p.threshold
        }
        for p in products
    ]

@app.post("/products")
def add_product(product: ProductCreate):
    db = SessionLocal()
    new_product = Product(**product.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    db.close()
    return new_product

@app.put("/products/{product_id}")
def update_quantity(product_id: int, update: ProductUpdate):
    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.quantity = update.quantity
    db.commit()
    db.close()
    return {"message": "Updated"}

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    db.close()
    return {"message": "Deleted"}

class ChatRequest(BaseModel):
    question: str
    inventory: List[Any] = []

@app.post("/chat")
async def chat(req: ChatRequest):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    context = "You are an AI assistant for a Supply Chain Inventory Tracker. "
    if req.inventory:
        context += f"Current inventory: {req.inventory}. "
    else:
        context += "The inventory is currently empty. "
    context += "Answer concisely based on this data."

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}"},
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": context},
                    {"role": "user", "content": req.question}
                ],
                "max_tokens": 300
            },
            timeout=30.0
        )
        data = response.json()

    choices = data.get("choices") or [{}]
    reply = choices[0].get("message", {}).get("content") or "Sorry, I could not get a response."
    return {"reply": reply}
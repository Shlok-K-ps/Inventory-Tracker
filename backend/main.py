from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
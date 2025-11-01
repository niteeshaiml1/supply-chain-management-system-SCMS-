from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.database import get_db
from typing import List

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(services.get_current_user)] # All routes require login
)

# --- Products ---

@router.post("/products", response_model=schemas.ProductRead, dependencies=[Depends(services.get_admin_user)])
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == product.supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/products", response_model=List[schemas.ProductRead])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).offset(skip).limit(limit).all()
    return products

# --- Warehouses ---

@router.post("/warehouses", response_model=schemas.WarehouseRead, dependencies=[Depends(services.get_admin_user)])
def create_warehouse(warehouse: schemas.WarehouseCreate, db: Session = Depends(get_db)):
    db_warehouse = models.Warehouse(**warehouse.dict())
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse

@router.get("/warehouses", response_model=List[schemas.WarehouseRead])
def read_warehouses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    warehouses = db.query(models.Warehouse).offset(skip).limit(limit).all()
    return warehouses

# --- Inventory Stock Management ---

@router.post("/stock", response_model=schemas.InventoryItemRead, dependencies=[Depends(services.get_warehouse_manager)])
def add_or_update_stock(item: schemas.InventoryItemCreate, db: Session = Depends(get_db)):
    # Check if product and warehouse exist
    db_product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db_warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == item.warehouse_id).first()
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Check if this item already exists in inventory
    db_item = db.query(models.InventoryItem).filter(
        models.InventoryItem.product_id == item.product_id,
        models.InventoryItem.warehouse_id == item.warehouse_id
    ).first()
    
    if db_item:
        # Update existing stock
        db_item.quantity += item.quantity
    else:
        # Create new inventory item
        db_item = models.InventoryItem(**item.dict())
        db.add(db_item)
    
    db.commit()
    db.refresh(db_item)
    
    # Check for re-order level
    if db_item.quantity < db_item.reorder_level:
        print(f"ALERT: Product ID {db_item.product_id} in Warehouse ID {db_item.warehouse_id} is low on stock! Qty: {db_item.quantity}")
        # In a real app, this would trigger an email or notification
        
    return db_item

@router.get("/stock/{product_id}", response_model=List[schemas.InventoryItemRead])
def get_stock_for_product(product_id: int, db: Session = Depends(get_db)):
    items = db.query(models.InventoryItem).filter(models.InventoryItem.product_id == product_id).all()
    if not items:
        raise HTTPException(status_code=404, detail="No stock found for this product")
    return items

@router.post("/batch-update", response_model=List[schemas.InventoryItemRead], dependencies=[Depends(services.get_warehouse_manager)])
def batch_update_stock(updates: List[schemas.InventoryBatchUpdate], db: Session = Depends(get_db)):
    """
    API for batch updates from IoT scanners.
    This assumes the 'quantity' sent is the *new total quantity*.
    """
    updated_items = []
    for update in updates:
        db_item = db.query(models.InventoryItem).filter(
            models.InventoryItem.product_id == update.product_id,
            models.InventoryItem.warehouse_id == update.warehouse_id
        ).first()
        
        if db_item:
            db_item.quantity = update.quantity
            
            # Check for re-order level
            if db_item.quantity < db_item.reorder_level:
                print(f"ALERT: Product ID {db_item.product_id} in Warehouse ID {db_item.warehouse_id} is low on stock! Qty: {db_item.quantity}")
            
            updated_items.append(db_item)
        else:
            # Optionally create new item if not found, or just skip
            print(f"Skipping update for non-existent item: Product {update.product_id}, Warehouse {update.warehouse_id}")
            
    db.commit()
    # We can't use db.refresh() on a list, so we'll just return the committed data
    return updated_items

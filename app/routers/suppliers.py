from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.database import get_db
from typing import List

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[Depends(services.get_current_user)]
)

@router.post("/", response_model=schemas.SupplierRead)
def create_supplier(
    supplier: schemas.SupplierCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(services.get_admin_user)
):
    """
    Create a new supplier (Admin Only).
    """
    db_supplier_email = db.query(models.Supplier).filter(models.Supplier.contact_email == supplier.contact_email).first()
    if db_supplier_email:
        raise HTTPException(status_code=400, detail="Email already registered for a supplier.")
        
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.get("/", response_model=List[schemas.SupplierRead])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get a list of all suppliers.
    """
    suppliers = db.query(models.Supplier).offset(skip).limit(limit).all()
    return suppliers

@router.get("/{supplier_id}", response_model=schemas.SupplierRead)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """
    Get details for a specific supplier.
    """
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_supplier

@router.put("/{supplier_id}", response_model=schemas.SupplierRead)
def update_supplier(
    supplier_id: int,
    supplier: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(services.get_admin_user)
):
    """
    Update a supplier's details (Admin Only).
    """
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    # Update only the fields that were sent
    update_data = supplier.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)
        
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(services.get_admin_user)
):
    """
    Delete a supplier (Admin Only).
    """
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    # Note: You might want to add logic here to prevent deleting a supplier
    # that has products associated with it. For this project, we'll allow it.
        
    db.delete(db_supplier)
    db.commit()
    return {"ok": True} # 204 No Content response won't send a body
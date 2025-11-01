from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.database import get_db
from typing import List

router = APIRouter(
    prefix="/shipments",
    tags=["Shipments"],
    dependencies=[Depends(services.get_current_user)]
)

@router.post("/", response_model=schemas.ShipmentRead)
def create_shipment(
    shipment: schemas.ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(services.get_warehouse_manager) # Admin or Warehouse Manager
):
    """
    Create a new shipment for a PROCESSED order.
    """
    db_order = db.query(models.Order).filter(models.Order.id == shipment.order_id).first()
    
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if db_order.status != schemas.OrderStatus.Processed:
        raise HTTPException(
            status_code=400, 
            detail=f"Order is in '{db_order.status}' status. Must be 'Processed' to ship."
        )
        
    existing_shipment = db.query(models.Shipment).filter(models.Shipment.order_id == shipment.order_id).first()
    if existing_shipment:
        raise HTTPException(
            status_code=400,
            detail=f"Shipment for Order ID {shipment.order_id} already exists."
        )

    db_shipment = models.Shipment(
        order_id=shipment.order_id,
        transporter_name=shipment.transporter_name,
        tracking_code=f"TRK-{shipment.order_id}-{db_order.owner_id}" # Simple tracking code
    )
    
    db_order.status = schemas.OrderStatus.Shipped
    
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    
    return db_shipment

@router.get("/", response_model=List[schemas.ShipmentRead])
def get_all_shipments(db: Session = Depends(get_db)):
    """
    Get a list of all shipments.
    """
    shipments = db.query(models.Shipment).all()
    return shipments

@router.get("/{shipment_id}", response_model=schemas.ShipmentRead)
def get_shipment(shipment_id: int, db: Session = Depends(get_db)):
    """
    Get details for a specific shipment by its ID.
    """
    db_shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return db_shipment

@router.post("/{shipment_id}/location", response_model=schemas.ShipmentLocation)
def update_shipment_location(
    shipment_id: int,
    location: schemas.ShipmentLocation,
    db: Session = Depends(get_db)
    # This endpoint could be protected by a special API key,
    # but for now we'll use the standard user auth.
):
    """
    Update the location of a shipment (e.g., from a GPS device).
    """
    db_shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # In a real app, you would save this to a separate tracking table.
    # For this project, we will just print it to the console.
    print(f"Shipment {shipment_id} location updated to: {location.latitude}, {location.longitude}")
    
    return location

@router.post("/{shipment_id}/deliver", response_model=schemas.ShipmentRead)
def mark_shipment_delivered(
    shipment_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(services.get_admin_user) # Only Admin can confirm
):
    """
    Mark a shipment as "Delivered".
    This also updates the parent Order's status to "Completed".
    """
    db_shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
        
    if db_shipment.status == schemas.ShipmentStatus.Delivered:
        raise HTTPException(status_code=400, detail="Shipment is already marked as delivered.")

    db_shipment.status = schemas.ShipmentStatus.Delivered
    
    db_order = db.query(models.Order).filter(models.Order.id == db_shipment.order_id).first()
    if db_order:
        db_order.status = schemas.OrderStatus.Completed
        
    db.commit()
    db.refresh(db_shipment)
    return db_shipment
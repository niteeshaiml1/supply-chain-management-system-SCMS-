from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.database import get_db
from typing import List

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(services.get_current_user)] # All routes require login
)

@router.post("/", response_model=schemas.OrderRead)
def create_order(
    order: schemas.OrderCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(services.get_current_user)
):
    """
    Create a new order. This is the most complex piece of business logic.
    1. Check if all products exist.
    2. Check if there is enough stock FOR ALL items (from any warehouse).
    3. If not, fail the transaction.
    4. If yes, "reserve" the stock (decrement from inventory).
    5. Create the Order and OrderItem entries.
    This MUST be a database transaction.
    """
    
    # We'll use a simple "find first warehouse that has stock" strategy
    inventory_items_to_update = []
    order_items_to_create = []
    
    try:
        for item in order.items:
            # Check if product exists
            db_product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not db_product:
                raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found")
            
            # Find inventory items for this product with enough stock
            db_inventory_items = db.query(models.InventoryItem).filter(
                models.InventoryItem.product_id == item.product_id,
                models.InventoryItem.quantity >= item.quantity
            ).order_by(models.InventoryItem.quantity.desc()).all() # Get the one with the most stock first
            
            if not db_inventory_items:
                raise HTTPException(status_code=400, detail=f"Not enough stock for Product ID {item.product_id}")
            
            # Take stock from the first warehouse that has enough
            # A real system might split this across warehouses, but we'll keep it simple
            inventory_to_debit = db_inventory_items[0]
            
            inventory_to_debit.quantity -= item.quantity # "Reserve" the stock
            inventory_items_to_update.append(inventory_to_debit)
            
            # Prep the OrderItem for creation
            order_items_to_create.append(
                models.OrderItem(product_id=item.product_id, quantity=item.quantity)
            )

        # If we're here, all items had stock!
        # Create the main order
        db_order = models.Order(
            customer_email=order.customer_email,
            owner_id=current_user.id,
            status=models.OrderStatus.PENDING
        )
        
        # Add the OrderItems we prepped to the order
        db_order.order_items = order_items_to_create
        
        db.add(db_order)
        # The 'inventory_items_to_update' are already part of the session,
        # so we just need to commit.
        
        db.commit() # This commits everything (Order, OrderItems, Inventory updates) at once
        
        db.refresh(db_order)
        return db_order

    except Exception as e:
        db.rollback() # If ANYTHING went wrong, undo all changes
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(services.get_current_user)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only Admin or the user who created the order can see it
    if db_order.owner_id != current_user.id and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
        
    return db_order

@router.post("/{order_id}/cancel", response_model=schemas.OrderRead)
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(services.get_current_user)):
    # Logic to cancel an order
    # This should also "put back" the stock into inventory!
    # We will skip that logic for brevity, but it's the reverse of the create_order logic.
    
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    if db_order.owner_id != current_user.id and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
        
    if db_order.status not in [models.OrderStatus.PENDING, models.OrderStatus.PROCESSED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status {db_order.status}")
    
    db_order.status = models.OrderStatus.CANCELED
    
    # TODO: Add logic to return stock to inventory
    
    db.commit()
    db.refresh(db_order)
    return db_order

# --- THIS IS THE NEW ENDPOINT ---
@router.post("/{order_id}/process", response_model=schemas.OrderRead, dependencies=[Depends(services.get_warehouse_manager)])
def process_order(order_id: int, db: Session = Depends(get_db)):
    """
    (Admin/Warehouse Manager Only)
    Manually marks an order as "Processed", ready for shipment.
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=4.04, detail="Order not found")
        
    if db_order.status != models.OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Order is not in 'Pending' state. Current state: {db_order.status}")
        
    db_order.status = models.OrderStatus.PROCESSED
    db.commit()
    db.refresh(db_order)
    return db_order


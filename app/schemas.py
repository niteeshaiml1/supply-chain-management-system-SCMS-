from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import enum

# --- Enums (for status) ---
class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Processed = "Processed"
    Shipped = "Shipped"
    Completed = "Completed"
    Cancelled = "Cancelled"

class ShipmentStatus(str, enum.Enum):
    InTransit = "In-Transit"
    Delivered = "Delivered"

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: str = "Retailer"

class UserRead(UserBase):
    id: int
    role: str
    class Config:
        from_attributes = True

# --- Supplier Schemas ---
class SupplierBase(BaseModel):
    name: str
    contact_email: EmailStr
    phone: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(SupplierBase):
    # All fields are optional for updating
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None

class SupplierRead(SupplierBase):
    id: int
    on_time_delivery_rate: float
    defect_rate: float
    class Config:
        from_attributes = True

# --- Inventory Schemas ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProductCreate(ProductBase):
    supplier_id: int

class ProductRead(ProductBase):
    id: int
    supplier_id: int
    class Config:
        from_attributes = True

class WarehouseBase(BaseModel):
    name: str
    location: str

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseRead(WarehouseBase):
    id: int
    class Config:
        from_attributes = True

class InventoryItemBase(BaseModel):
    quantity: int
    reorder_level: int

class InventoryItemCreate(InventoryItemBase):
    product_id: int
    warehouse_id: int

class InventoryItemRead(InventoryItemBase):
    id: int
    product_id: int
    warehouse_id: int
    class Config:
        from_attributes = True

class InventoryBatchUpdate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity_change: int # Positive to add, negative to remove

# --- Order Schemas ---
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemRead(OrderItemBase):
    id: int
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    customer_email: EmailStr

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderRead(OrderBase):
    id: int
    owner_id: int
    status: OrderStatus
    created_at: datetime
    order_items: List[OrderItemRead] = []
    class Config:
        from_attributes = True

# --- Shipment Schemas ---
class ShipmentBase(BaseModel):
    transporter_name: str

class ShipmentCreate(ShipmentBase):
    order_id: int

class ShipmentRead(ShipmentBase):
    id: int
    order_id: int
    tracking_code: str
    status: ShipmentStatus = ShipmentStatus.InTransit
    class Config:
        from_attributes = True

class ShipmentLocation(BaseModel):
    latitude: float
    longitude: float
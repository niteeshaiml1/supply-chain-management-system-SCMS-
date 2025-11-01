from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Enum
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import enum

# --- Enums for Statuses ---
class OrderStatus(str, enum.Enum):
    PENDING = "Pending"
    PROCESSED = "Processed"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELED = "Canceled"

class ShipmentStatus(str, enum.Enum):
    IN_TRANSIT = "In-Transit"
    DELIVERED = "Delivered"

# --- Core Models ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Retailer") # Admin, Supplier, Warehouse Manager, Retailer

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_email = Column(String, unique=True, index=True)
    phone = Column(String)
    
    # Performance metrics
    on_time_delivery_rate = Column(Float, default=100.0)
    defect_rate = Column(Float, default=0.0)
    
    # Relationship: A supplier can supply many products
    products = relationship("Product", back_populates="supplier")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="products")
    
    # Relationship: A product can be in many inventory items and order items
    inventory_items = relationship("InventoryItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    
    # Relationship: A warehouse holds many inventory items
    inventory_items = relationship("InventoryItem", back_populates="warehouse")

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, default=10) # Alert when quantity drops below this
    
    product_id = Column(Integer, ForeignKey("products.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    
    product = relationship("Product", back_populates="inventory_items")
    warehouse = relationship("Warehouse", back_populates="inventory_items")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_email = Column(String) # For a retailer
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship: An order is made by a user (Retailer)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")
    
    # Relationship: An order has many items and one shipment
    order_items = relationship("OrderItem", back_populates="order")
    shipment = relationship("Shipment", back_populates="order", uselist=False)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, index=True)
    transporter_name = Column(String)
    tracking_code = Column(String, unique=True, index=True)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.IN_TRANSIT)
    
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True) # One-to-one with Order
    order = relationship("Order", back_populates="shipment")

from fastapi import FastAPI
from app import models
from app.database import engine
from app.routers import auth, suppliers, inventory, orders, shipments, analytics # Import ALL routers

# This line creates all the tables in your Supabase DB!
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Supply Chain Management System (SCMS)")

# Include your routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(suppliers.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(shipments.router)
app.include_router(analytics.router) # <-- ADD THIS LINE


@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart SCMS API"}
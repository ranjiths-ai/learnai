from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Initialize FastAPI App
app = FastAPI(
    title="Item Management API",
    description="An example demonstrating Pydantic models and async endpoints.",
    version="1.0.0",
)

# ------------------------------------------------------------------
# 0.Pre-requisites: Install FastAPI and Uvicorn
# using python -m pip install fastapi uvicorn
# --------------------------------------------------


# ------------------------------------------------------------------
# 1. DEFINE PYDANTIC MODELS
# ------------------------------------------------------------------

class ItemBase(BaseModel):
    name: str = Field(..., example="Wireless Mouse", description="Name of the item")
    description: Optional[str] = Field(None, example="Ergonomic optical mouse", description="Optional item description")
    price: float = Field(..., gt=0, example=29.99, description="Price must be greater than 0")
    tax: Optional[float] = Field(None, ge=0, example=2.40, description="Optional tax value")


class ItemCreate(ItemBase):
    """Schema used when creating a new item."""
    pass


class ItemResponse(ItemBase):
    """Schema returned to clients, including the generated ID."""
    id: int

    class Config:
        orm_mode = True


# In-memory database for demonstration purposes
db: List[dict] = []


# ------------------------------------------------------------------
# 2. CREATE ASYNC ENDPOINTS
# ------------------------------------------------------------------

@app.post(
    "/items/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an Item",
)
async def create_item(item: ItemCreate):
    """Async endpoint to create a new item."""
    new_id = len(db) + 1
    item_dict = item.dict()
    item_dict["id"] = new_id
    db.append(item_dict)
    return item_dict


@app.get(
    "/items/",
    response_model=List[ItemResponse],
    summary="Get All Items",
)
async def get_items():
    """Async endpoint to retrieve all stored items."""
    return db


@app.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Get Item by ID",
)
async def get_item(item_id: int):
    """Async endpoint to retrieve a single item by its ID."""
    for item in db:
        if item["id"] == item_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with ID {item_id} not found",
    )


@app.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an Item",
)
async def delete_item(item_id: int):
    """Async endpoint to delete an item by its ID."""
    for index, item in enumerate(db):
        if item["id"] == item_id:
            db.pop(index)
            return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with ID {item_id} not found",
    )
    
# -------------------------------------------------------------------------------------------------------------------------
# 3.Torun the FastAPI app using Uvicorn  
# uvicorn main:app --reload
# copy the url's (http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc) paste in browser to see the FastAPI Swagger UI
# -------------------------------------------------------------------------------------------------------------------------
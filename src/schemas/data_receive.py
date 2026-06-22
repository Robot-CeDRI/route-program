from pydantic import BaseModel
from typing import List, Any

# ==========================================
# MAIN SCHEMA (REQUEST)
# ==========================================

class ModelDataValidator(BaseModel):
    x: float
    y: float
    people: int
    is_helping: bool
    moving : bool
    unique_people: List[str]
# ==========================================
# RESPONSE SCHEMA (WHAT IS RETURNED)
# ==========================================

class ModelDataResponse(BaseModel):
    message: str
    error: bool
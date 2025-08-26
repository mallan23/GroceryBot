# This file defines the core objects for the groecery bot application.
#we need a class for our weekly meal plan, and each meal, recipe

from pydantic import BaseModel
from typing import List, Dict

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str

class Meal(BaseModel):
    name: str
    ingredients: List[Ingredient]

class WeeklyPlan(BaseModel):
    days: Dict[str, Dict[str, Meal]]
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

# days is a dictionary with keys as day names and vlaue as another dictionary with meal names as keys and Meal objects as values
class WeeklyPlan(BaseModel):
    days: Dict[str, Dict[str, Meal]]
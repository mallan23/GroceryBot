# this clas generates a shopping list from a weekly meal plan by aggregating ingredients from each meal

from models import Ingredient
from agent import Agent

#requires context to have a weekly_plan key with WeeklyPlan object
class IngredientCollectorAgent(Agent):
    def run(self, context): 
        plan = context["weekly_plan"] # context dictionary stores plan and will store shopping list
        agg = {} #for collecting ingredients
        
        # for each day in the weekly plan, for each meal, for each ingredient, aggregate quantities
        for day in plan.days.values():
            for meal in day.values():
                for ing in meal.ingredients: #for each ingredient creates a key using the name and unit
                    key = (ing.name.lower(), ing.unit) 
                    agg[key] = agg.get(key, 0) + ing.quantity # adds quantity to the existing key

        # creates list of ingredient objects from the aggregated dictionary
        # stores this in context under "shopping_list" key
        context["shopping_list"] = [
            Ingredient(name=name, unit=unit, quantity=qty)
            for (name, unit), qty in agg.items()
        ]
        return context
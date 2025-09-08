# this agent is responsible for adding the generated meal plan, the meals, the ingredients, and the shopping items to the database
#the import of db will execute the top level code in db.py, creating the tables if they don't exist and configure the engine


from agent import Agent
from db import SessionLocal, MealPlan, Meal, MealIngredient, ShoppingItem

class PersistenceAgent(Agent):
    def run(self, context):
        weekly_plan = context["weekly_plan"]
        tags = context.get("dietary_tags", [])
        plan_json = weekly_plan.json()

        with SessionLocal() as session:
            # begin a transaction
            with session.begin():
                # 1. Create the MealPlan
                db_plan = MealPlan(dietary_tags=tags, plan_json=plan_json)
                session.add(db_plan)
                session.flush() # Ensure db_plan.id is populated

                # 2. Persist Meals & Ingredients, skipping duplicates
                for day, meals in weekly_plan.days.items():
                    for meal_type, meal in meals.items():
                        # a) Try to load an existing meal by name
                        db_meal = (
                            session.query(Meal)
                                   .filter_by(meal_name=meal.name)
                                   .one_or_none()
                        )
                        if not db_meal:
                            db_meal = Meal(meal_name=meal.name)
                            session.add(db_meal)
                            session.flush()  # assign ID

                        # b) For each ingredient, insert only if it doesn't exist (means meals can be updated)
                        for ing in meal.ingredients:
                            exists = (
                                session.query(MealIngredient)
                                       .filter_by(meal_id=db_meal.id, name=ing.name)
                                       .one_or_none()
                            )
                            if not exists:
                                session.add(MealIngredient(
                                    meal_id=db_meal.id,
                                    name=ing.name,
                                    quantity=ing.quantity,
                                    unit=ing.unit
                                ))

                # 3. Persist Shopping Items
                for ing in context["shopping_list"]:
                    session.add(ShoppingItem(
                        plan=db_plan,
                        name=ing.name,
                        quantity=ing.quantity,
                        unit=ing.unit
                    ))

            # transaction commits here

        context["db_plan_id"] = db_plan.id
        return context
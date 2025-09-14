import os
import requests #type: ignore
import re
from sqlalchemy import text #type: ignore
from sqlalchemy.orm import Session #type: ignore
from db import SessionLocal, NutritionLookup, Meal, MealIngredient, ShoppingItem
from typing import Optional

USDA_API_KEY = os.getenv("USDA_API_KEY")

class NutritionAgent:
    def run(self, ctx: dict) -> dict:
        print("Running NutritionAgent...")
        plan_id = ctx["db_plan_id"]

        if not USDA_API_KEY: #confirm API key is set
            raise RuntimeError("USDA_API_KEY environment variable is not set. Please set it before running the application.")
        
        with SessionLocal() as session:
            # Ensure nutrition_lookup is populated from shopping_items
            items = session.query(ShoppingItem).filter_by(plan_id=plan_id).all()
            for item in items:
                # get_calories_for_item writes into nutrition_lookup
                self.get_calories_for_item(session, item.name)

            # Collect all the meal names from the weekly plan
            weekly_plan = ctx["weekly_plan"]
            meal_names = [
                meal_obj.name
                for meals_by_day in weekly_plan.days.values()
                for meal_obj in meals_by_day.values()
            ]
            # load only those meals from Postgres
            meals = (
                session.query(Meal)
                .filter(Meal.meal_name.in_(meal_names))
                .all()
            )

            # Process each meal only if calories_total is NULL
            #meals = session.query(Meal).all()
            for meal in meals:
                if meal.calories_total is not None:
                    continue  # already calculated

                total_cals = 0.0
                # load ingredients for this meal
                ings = session.query(MealIngredient) \
                             .filter_by(meal_id=meal.id) \
                             .all()

                # for each ingredient, if it doesnt have a calper100 then query the lookup
                #if it doesnt exist in the lookup call the api
                for ing in ings: 
                    #get or fetch per 100g cals and fdc_id
                    if ing.cals_per_100g is None:
                        rec = session.get(NutritionLookup, self.normalize(ing.name))
                        if rec:
                            ing.cals_per_100g = rec.calories_per_100g
                            ing.fdc_id       = rec.usda_fdc_id
                        else:
                            # fallback: query USDA live
                            c100, fdc = self.get_calories_for_item(session, ing.name)
                            ing.cals_per_100g = c100
                            ing.fdc_id       = fdc
                        session.add(ing)
                    
                    #if still missing (meaning no match), skip
                    if ing.cals_per_100g is None:
                        print(f"[WARN] No calorie data for '{ing.name}', skipping.")
                        continue

                    # convert quantity+unit ➔ grams
                    grams = self.convert_to_grams(ing.quantity, ing.unit, ing.fdc_id)
                    # compute total cals for this ingredient
                    ing.cals_total = (grams / 100.0) * ing.cals_per_100g
                    total_cals    += ing.cals_total


                    # lookup per-100g cals from meal_ingredient if cached
                    #c100 = ing.cals_per_100g
                    #fdc  = ing.fdc_id

                    # else fetch from nutrition_lookup
                    #if c100 is None:
                    #    rec = session.get(NutritionLookup, self.normalize(ing.name))
                    #    if rec:
                    #        c100 = rec.calories_per_100g
                    #        fdc  = rec.usda_fdc_id

                        # update MealIngredient row for future
                        #ing.cals_per_100g = c100
                        #ing.fdc_id       = fdc
                        #session.add(ing)

                # 3) store meal total
                meal.calories_total = total_cals
                session.add(meal)
                print(f"Meal '{meal.meal_name}' total calories: {total_cals:.1f}")

            session.commit()

        ctx["calories_done"] = True
        return ctx

    #for making safe API calls with error handling and timeouts
    @staticmethod
    def safe_api_get(url: str, params: dict) -> Optional[dict]:
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception as e:
                print(f"[ERROR] Failed to parse JSON from {url}: {e}")
                print("Raw response:", resp.text[:500])
                return None
        except requests.RequestException as e:
            print(f"[ERROR] Request to {url} failed: {e}")
            return None
        
    def normalize(self, name: str) -> str:
        # Remove patterns like "1.0 cup", "2 grams", etc.
        name = re.sub(r"\b\d*\.?\d+\s*[a-zA-Z]+\b", "", name)
        # remove descriptors that often cause noise — tweak as needed
        remove_words = r"\b(organic|fresh|large|small|sliced|diced|chopped|minced|grilled|roasted|pan-fried|fried|baked|boiled|cooked)\b"
        name = re.sub(remove_words, "", name)
        # Remove any remaining non-letter characters and extra spaces
        name = re.sub(r"[^a-zA-Z\s]", "", name)
        # Collapse multiple spaces and strip
        name = re.sub(r"\s+", " ", name).strip().lower()
        return name

    def fetch_food_portions(self, fdc_id: str) -> list[dict]:
        """Fetches the 'foodPortions' array from the details endpoint."""
        url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
        data = self.safe_api_get(url, params={"api_key": USDA_API_KEY})
        if not data:
            return []
        return data.get("foodPortions", [])
    
    def match_portion_unit(self, portions: list[dict], unit_lower: str) -> Optional[float]:
        """
        Look for an exact match on measureUnit or in portionDescription,
        return its gramWeight.
        """
        for p in portions:
            # exact match on measureUnit
            if p.get("measureUnit", "").lower() == unit_lower:
                return p.get("gramWeight")
            # loose match on portionDescription (e.g. "1 slice", "1 piece")
            desc = p.get("portionDescription", "").lower()
            if unit_lower in desc:
                return p.get("gramWeight")
        return None

    def convert_to_grams(self, qty: float, unit: str, fdc_id: Optional[str]) -> float:
        unit = unit.lower().strip()
        # if already g/ml, return directly, if an easy convert perform it
        if unit in ("g", "gram", "grams"):
            return qty
        if unit in ("kg", "kilogram", "kilograms"):
            return qty * 1000
        if unit in ("ml",):
            return qty  # assume water density
        if unit in ("l", "liter", "litre"):
            return qty * 1000
        
        #if not easy, try API call to see if serving size exists
        if fdc_id:
            portions = self.fetch_food_portions(fdc_id)
            #gp = self.match_portion_unit(portions, unit)
            gp = None
            for p in portions:
                if "gramWeight" in p:
                    gp = p["gramWeight"]
                    break
            #gp = portions.get("gramWeight") if portions else None
            if gp is not None:
                return qty * gp

        # if no portion size, treat as volume, approximate 240 g per cup, etc.
        cups = {"cup": 240, "tablespoon": 15, "tablespoons": 15, "teaspoon": 5, "teaspoons": 5, "cloves": 5, "piece": 50, "slice": 30}
        for k, v in cups.items():
            if k in unit:
                return qty * v
        print(f"[WARN] Unknown unit '{unit}' for quantity {qty}, assuming 0 grams.")
        return 0  # if cant find, assume 0 grams

    def extract_energy_kcal_from_food(self, food_obj: dict) -> float:
        """
        Return kcal value from first energy nutrient match, assumes it is based on per 100g.
        """
        for n in food_obj.get("foodNutrients", []):
            if "energy" in n.get("nutrientName", "").lower():
                return float(n.get("value", 0))
        return 0.0

    def get_calories_for_item(
        self, session: Session, raw_name: str
    ) -> tuple[float, str]:
        """
        Normalize raw_name, lookup in nutrition_lookup.
        If missing, call USDA, fuzzy‐match, insert into lookup.
        Returns (kcal_per_100g, usda_fdc_id) or none if no match.
        """
        norm = self.normalize(raw_name)

        # Check table first to see if stored
        rec = session.get(NutritionLookup, norm)
        if rec:
            return rec.calories_per_100g, rec.usda_fdc_id

        # call USDA API then parses the json and grabs the foods list
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "api_key": USDA_API_KEY,
            "query": norm,
            "pageSize": 20,
            "dataType": ["Foundation"],
        }
        resp = self.safe_api_get(url, params=params)
        # No foods returned → no match
        if not resp or "foods" not in resp:
            print(f"No USDA results for '{raw_name}' → skipping")
            return None, None

        data = resp.get("foods", [])

        #fuzzy‐match description with food item name, scores to find best matching candidate
        candidates = {f["description"]: f for f in data}
        scores = [
            (desc, self.score_candidate(norm, desc)) for desc in candidates
        ]
        best, _ = max(scores, key=lambda x: x[1], default=(None, 0))
        food = candidates.get(best, {})
        fdc_id = str(food.get("fdcId", ""))
        kcal   = self.extract_energy_kcal_from_food(food)

        #insert into nutrition_lookup
        session.execute(
            text(
                "INSERT INTO nutrition_lookup "
                "(name, raw_name, usda_fdc_id, calories_per_100g) "
                "VALUES (:n, :r, :id, :k) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"n": norm, "r": raw_name, "id": fdc_id, "k": kcal},
        )
        session.commit()
        return kcal, fdc_id

    @staticmethod
    def score_candidate(query: str, desc: str) -> float:
        """
        Combined scoring using multiple fuzzy measures + presence checks.
        Returns a 0..100-ish score.
        """
        from rapidfuzz import fuzz #type: ignore

        s1 = fuzz.token_set_ratio(query, desc)
        s2 = fuzz.token_sort_ratio(query, desc)
        s3 = fuzz.partial_ratio(query, desc)
        tokens_q = set(query.split())
        tokens_d = set(re.findall(r"\w+", desc.lower()))
        bonus = 10 * (len(tokens_q & tokens_d) / max(1, len(tokens_q))) #up to +10 if all tokens match
        return 0.4 * s1 + 0.3 * s2 + 0.2 * s3 + bonus #weighted average
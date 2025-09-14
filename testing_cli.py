import typer #type: ignore
import json
from pathlib import Path
from typing import List, Dict, Any
from llm_agent import LLMMealPlanAgent
from collector_agent import IngredientCollectorAgent
from agent import Agent
from typing import List, Dict, Any
from persistence_agent import PersistenceAgent
from nutrition_agent import NutritionAgent
from models import WeeklyPlan

app = typer.Typer()


# Map short names to classes
AGENTS_MAP = {
    "mealplan": LLMMealPlanAgent,
    "ingredients": IngredientCollectorAgent,
    "persistence": PersistenceAgent,
    "nutrition": NutritionAgent,
}

def save_ctx(ctx: Dict[str, Any], name: str):
    ctx_to_save = ctx.copy()
    # Convert weekly_plan to dict if it's a Pydantic model
    wp = ctx_to_save.get("weekly_plan")
    if hasattr(wp, "model_dump"):
        ctx_to_save["weekly_plan"] = wp.model_dump()
    elif hasattr(wp, "dict"):
        ctx_to_save["weekly_plan"] = wp.dict()
    Path("/content/drive/MyDrive/artifacts").mkdir(exist_ok=True)
    with open(f"/content/drive/MyDrive/artifacts/{name}.json", "w") as f:
        json.dump(ctx_to_save, f, indent=2, default=str)

def load_ctx(fixture: str) -> Dict[str, Any]:
    with open(fixture, "r") as f:
        ctx = json.load(f)
    # Convert weekly_plan dict back to WeeklyPlan model if present
    if "weekly_plan" in ctx and isinstance(ctx["weekly_plan"], dict):
        ctx["weekly_plan"] = WeeklyPlan(**ctx["weekly_plan"])
    return ctx

'''
def save_ctx(ctx: Dict[str, Any], name: str):
    Path("/content/drive/MyDrive/artifacts").mkdir(exist_ok=True)
    with open(f"/content/drive/MyDrive/artifacts/{name}.json", "w") as f:
        json.dump(ctx, f, indent=2, default=str)

# Given a fixture file, loads the json content into a dictionary
def load_ctx(fixture: str) -> Dict[str, Any]:
    with open(fixture, "r") as f:
        return json.load(f)
'''
@app.command()
def run(
    agents: List[str] = typer.Argument(..., help="Agents to run in order, or 'all'"),
    fixture: str = typer.Option(None, help="Context file to load (if not running all)"),
    model: str = typer.Option("mistralai/Mistral-7B-Instruct-v0.3"),
    device: str = typer.Option("cuda"),
    diet: str = typer.Option("", help="Dietary tags: vegan, keto, etc."),
):
    """
    Run one or more agents independently, or the full pipeline ('all').
    """
    # Resolve the sequence of agents to run
    if len(agents) == 1 and agents[0].lower() == "all":
        selected = ["mealplan", "ingredients", "persistence", "nutrition"]
    else:
        selected = [a.lower() for a in agents]
        for a in selected:
            if a not in AGENTS_MAP:
                raise ValueError(f"Unknown agent: {a}")

    # Initial context - if starting with mealplan, use diet; else load from fixture
    if "mealplan" in selected and selected[0] == "mealplan":
        ctx = {"dietary_tags": diet}  # starting point for plan
    elif fixture:
        ctx = load_ctx(fixture)
        ctx["weekly_plan"] = json.loads(ctx["weekly_plan"])
        ctx["weekly_plan"] = WeeklyPlan(**ctx["weekly_plan"])
    else:
        raise typer.BadParameter("Must provide a fixture file unless running 'all' or starting with mealplan.")

    # Run chosen agents
    for name in selected:
        print(f"\n Running agent: {name}")
        if name == "mealplan":
            agent = AGENTS_MAP[name](model_name=model, device=device)
        else:
            agent = AGENTS_MAP[name]()
        ctx = agent.run(ctx)
        save_ctx(ctx, name)
        print(f"Finished {name}. Context snapshot saved to /content/drive/MyDrive/artifacts/{name}.json")

    print("\n Done. Final context:")
    print(json.dumps(ctx, indent=2, default=str))


if __name__ == "__main__":
    app()

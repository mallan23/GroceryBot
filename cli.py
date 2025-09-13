# defines a command-line interface for the grocery bot application using Typer
# This CLI allows users to generate a weekly meal plan and shopping list based on dietary preferences.
# command line arguments include dietary tags, model name, and device type (CPU or GPU). 

import typer #type: ignore
from llm_agent import LLMMealPlanAgent
from collector_agent import IngredientCollectorAgent
from agent import Agent
from typing import List, Dict, Any
from persistence_agent import PersistenceAgent
#from nutrition_agent import NutritionAgent
#from query_agent import QueryAgent

app = typer.Typer()

#coordinates the execution of multiple agents in sequence
#each agent modifies the context dictionary, which is passed to the next agent
def orchestrate(agents: List[Agent], init_ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx = init_ctx.copy()
    for agent in agents:
        print(f"Running agent: {agent.__class__.__name__}")
        ctx = agent.run(ctx) #passes context to each agent's run method
        print(f"Context after {agent.__class__.__name__}: {ctx}")
    return ctx

#receives diet, model, and device as command line options
@app.command()
def plan(diet: str = typer.Option("", help="Dietary tags: vegan, keto, etc."),
         model: str = typer.Option("mistralai/Mistral-7B-Instruct-v0.3", help="HuggingFace model name"),
         device: str = typer.Option("cpu", help="cpu or cuda")):
    """
    Generate weekly meal plan & shopping list by creating two agent objects. Then persist the results.
    """
    agents = [
        LLMMealPlanAgent(model_name=model, device=device),
        IngredientCollectorAgent(),
        PersistenceAgent()
    ]
    result = orchestrate(agents, {"dietary_tags": diet})
    # Print in a readable way
    typer.echo(f"Saved plan with ID: {result['db_plan_id']}")
    typer.echo("Weekly Plan:")
    if "weekly_plan" in result:
        typer.echo(result["weekly_plan"].model_dump_json(indent=2))
    else:
        typer.echo("No weekly plan generated.")

    typer.echo("\nShopping List:")
    for ing in result["shopping_list"]:
        typer.echo(f"- {ing.quantity} {ing.unit} {ing.name}")

# execute the app when this script is run directly
if __name__ == "__main__":
    app()
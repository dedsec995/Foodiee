import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.state import AgentState

def printer(state: AgentState):
    """
    Pretty prints the final output using rich:
    - Ingredients table
    - Shopping/missing list table (if present)
    - Numbered instructions
    """
    console = Console()
    last_message = state["messages"][-1]
    content = last_message.content

    if isinstance(content, str):
        try:
            data = json.loads(content)
        except Exception:
            console.print(content)
            return
    else:
        data = content

    def show_ingredients(ingredients: dict):
        table = Table(title="📝 Ingredients")
        table.add_column("Ingredient", style="cyan")
        table.add_column("Quantity", style="magenta")
        table.add_column("Unit", style="green")
        for name, det in ingredients.items():
            table.add_row(
                str(name),
                str(det.get("quantity", "")),
                str(det.get("unit", "")),
            )
        console.print(table)

    def show_shopping_list(missing: dict):
        if not missing: return
        table = Table(title="🛒 Shopping List (Missing)")
        table.add_column("Item", style="yellow")
        table.add_column("Required", style="magenta")
        table.add_column("Available", style="cyan")
        table.add_column("Unit", style="green")
        for name, det in missing.items():
            table.add_row(
                str(name),
                str(det.get("required", "")),
                str(det.get("available", "")),
                str(det.get("unit", "")),
            )
        console.print(table)

    def show_instructions(instructions: list):
        steps = "\n".join(f"[bold green]{i+1}.[/bold green] {step}" for i, step in enumerate(instructions))
        console.print(Panel(steps, title="👩‍🍳 Cooking Instructions", style="bright_blue"))

    def show_inventory(updated_inventory, max_items=10):
        table = Table(title=f"📦 Updated Inventory (showing first {max_items})")
        table.add_column("Item", style="blue")
        table.add_column("Quantity", style="magenta")
        table.add_column("Unit", style="green")
        for i, (item, det) in enumerate(updated_inventory.items()):
            if i >= max_items: break
            table.add_row(str(item), str(det.get("quantity", "")),
 str(det.get("unit", "")))
        console.print(table)

    recipe = None
    instructions = None
    ingredients = None

    if "scaled_recipe" in data:
        recipe = data["scaled_recipe"]
    elif "recipe" in data:
        recipe = data["recipe"]
    if recipe:
        ingredients = recipe.get("ingredients")
        instructions = recipe.get("instructions")
        if ingredients:
            show_ingredients(ingredients)
        if instructions:
            show_instructions(instructions)

    missing_list = data.get("missing_list")
    if missing_list:
        show_shopping_list(missing_list)

    console.print("[bold green]✅ All done![/bold green] If a shopping list appeared above, you need to buy missing items.")

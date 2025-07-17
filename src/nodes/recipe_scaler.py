import json
from langchain_core.messages import ToolMessage
from src.state import AgentState

def recipe_scaler(state: AgentState):
    """Scales the recipe intelligently based on servings and inventory."""
    
    recipe_tool_call = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            recipe_tool_call = msg.tool_calls[0]
            break
    if recipe_tool_call is None:
        raise ValueError("No tool call found in messages for scaling recipe.")

    recipe = recipe_tool_call["args"]
    servings = int(state["servings"])
    inventory = state.get("inventory", {}).get("items", {})

    scaled_recipe = recipe.copy()
    scaled_ingredients = {}

    non_scalable_units = {"to taste", "", "bunch", "medium", "pinch"}

    for ingredient, info in recipe["ingredients"].items():
        if not info:
            continue
        qty = info.get("quantity")
        unit = info.get("unit", "").lower()

        try:
            amount = float(qty)
        except (ValueError, TypeError):
            scaled_ingredients[ingredient] = info
            continue

        if unit in non_scalable_units:
            scaled_amount = amount
        else:
            scaled_amount = amount * (servings / 2)

        scaled_ingredients[ingredient] = {
            "quantity": str(scaled_amount) if scaled_amount % 1 else str(int(scaled_amount)),
            "unit": unit
        }

    scaled_recipe["ingredients"] = scaled_ingredients

    state["messages"].append(
        ToolMessage(
            tool_call_id=recipe_tool_call["id"],
            content=json.dumps({"scaled_recipe": scaled_recipe})
        )
    )
    return state

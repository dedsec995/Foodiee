import json
from langchain_core.messages import ToolMessage
from src.state import AgentState

def inventory_fetcher(state: AgentState):
    """Fetches the ingredients from inventory for the recipe."""
    with open("inventory.json", "r") as f:
        inventory = json.load(f)
    state["inventory"] = inventory

    recipe_tool_call = state["messages"][-1].tool_calls[0]
    recipe_ingredients = recipe_tool_call["args"]["ingredients"]

    inventory_items = inventory.get("items", {}).keys()
    missing_items = {}
    for item, quantity in recipe_ingredients.items():
        if item not in inventory_items:
            missing_items[item] = quantity

    if missing_items:
        state["messages"].append(ToolMessage(tool_call_id=recipe_tool_call["id"], content=json.dumps({"missing_items": missing_items})))
    else:
        state["messages"].append(ToolMessage(tool_call_id=recipe_tool_call["id"], content=json.dumps({"recipe": recipe_tool_call["args"]})))

    return state

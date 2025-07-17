import json
from langchain_core.messages import ToolMessage
from src.state import AgentState

def inventory_manager(state: AgentState):
    """
    Updates inventory.json by subtracting the used ingredients as per the scaled recipe.
    If any ingredient is insufficient, add it to missing_list, but still attempt to subtract whatever is available.
    """
    inventory_file = "inventory.json"
    missing_list = {}
    
    with open(inventory_file, "r") as f:
        inventory = json.load(f)
    items = inventory.get("items", {})

    last_msg = state["messages"][-1]
    content = json.loads(last_msg.content)
    extended = content.get("scaled_recipe", content.get("recipe", {}))
    scaled_ingredients = extended.get("ingredients", {})

    for ingredient, data in scaled_ingredients.items():
        req_qty = data.get("quantity")
        unit = data.get("unit", "").lower()
        try:
            req_amt = float(req_qty)
        except (ValueError, TypeError):
            continue

        inv_item = items.get(ingredient)
        if inv_item:
            inv_amt = inv_item.get("quantity")
            inv_unit = inv_item.get("unit", "").lower()
            try:
                inv_amt = float(inv_amt)
            except (ValueError, TypeError):
                inv_amt = req_amt

            if inv_unit == unit:
                if inv_amt >= req_amt:
                    items[ingredient]["quantity"] = str(inv_amt - req_amt)
                else:
                    missing_list[ingredient] = {
                        "required": str(req_amt),
                        "available": str(inv_amt),
                        "unit": unit
                    }
                    items[ingredient]["quantity"] = "0"
            else:
                missing_list[ingredient] = {
                    "required": str(req_amt),
                    "available": str(inv_amt),
                    "unit": f"{unit}/{inv_unit}"
                }
        else:
            missing_list[ingredient] = {
                "required": str(req_amt),
                "available": "0",
                "unit": unit
            }

    inventory['items'] = items
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=4)

    state["messages"].append(
        ToolMessage(
            tool_call_id="inventory_manager",
            content=json.dumps({
                "missing_list": missing_list, 
                "updated_inventory": items,
                "scaled_recipe": extended  # <------ FIX!
            })
        )
    )
    return state

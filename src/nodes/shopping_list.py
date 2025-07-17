import os
import json
from src.state import AgentState

def shopping_list(state: AgentState):
    """
    Generates a shopping list for missing ingredients, 
    and saves/updates it in shopping_list.json.
    """
    last_message = state["messages"][-1]
    result = json.loads(last_message.content)
    missing = result.get("missing_list", {})

    shopping_list_file = "shopping_list.json"
    if os.path.exists(shopping_list_file):
        with open(shopping_list_file, "r") as f:
            shopping = json.load(f)
    else:
        shopping = {}

    for item, details in missing.items():
        req_qty = details.get("required", "0")
        unit = details.get("unit", "")

        if item in shopping and shopping[item].get("unit", "") == unit:
            try:
                sum_qty = float(shopping[item]["quantity"]) + float(req_qty)
                if sum_qty.is_integer():
                    sum_qty = int(sum_qty)
                shopping[item]["quantity"] = str(sum_qty)
            except Exception:
                shopping[item]["quantity"] = req_qty
        else:
            shopping[item] = {
                "quantity": req_qty,
                "unit": unit
            }
    
    with open(shopping_list_file, "w") as f:
        json.dump(shopping, f, indent=4)

    return state

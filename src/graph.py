import json
from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.nodes import (
    recipe_fetcher,
    inventory_fetcher,
    recipe_scaler,
    inventory_manager,
    shopping_list,
    printer,
)

def inventory_branch(state: AgentState):
    last_msg = state["messages"][-1]
    try:
        content = json.loads(last_msg.content)
        missing = content.get("missing_list", {})
        if missing:
            return "shopping_list"
    except Exception:
        pass
    return "printer"

workflow = StateGraph(AgentState)

workflow.add_node("recipe_fetcher", recipe_fetcher)
workflow.add_node("inventory_fetcher", inventory_fetcher)
workflow.add_node("recipe_scaler", recipe_scaler)
workflow.add_node("inventory_manager", inventory_manager)
workflow.add_node("shopping_list", shopping_list)
workflow.add_node("printer", printer)

workflow.set_entry_point("recipe_fetcher")

workflow.add_edge("recipe_fetcher", "inventory_fetcher")
workflow.add_edge("inventory_fetcher", "recipe_scaler")
workflow.add_edge("recipe_scaler", "inventory_manager")
workflow.add_conditional_edges(
    "inventory_manager",
    inventory_branch,
    {
        "shopping_list": "shopping_list",
        "printer": "printer"
    }
)
workflow.add_edge("shopping_list", "printer")
workflow.add_edge("printer", END)

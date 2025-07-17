

import os
import json
from typing import Annotated, List, TypedDict

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.runnables.graph_mermaid import draw_mermaid_png
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

# ------------------ MODELS ------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(temperature=0, model_name="llama3-70b-8192", api_key=GROQ_API_KEY)

# ------------------ TOOLS ------------------

class Recipe(BaseModel):
    """Represents a recipe with ingredients and instructions."""
    recipe_name: str = Field(description="The name of the recipe.")
    ingredients: dict = Field(description="A dictionary of ingredients and their quantities.")
    instructions: List[str] = Field(description="A list of instructions for the recipe.")

class ShoppingList(BaseModel):
    """Represents a shopping list with formatted items."""
    shopping_list: dict = Field(description="A dictionary of missing items with their quantities and units, e.g. {'flour': {'quantity': 500, 'unit': 'g'}}")


# ------------------ STATE ------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    inventory: dict
    shopping_list: dict
    servings: int

# ------------------ NODES ------------------

def recipe_fetcher(state: AgentState):
    """Fetches a recipe based on the user's request."""
    search = DuckDuckGoSearchRun()
    dish_query = state["messages"][0]
    search_results = search.run(f"recipe for {dish_query}")

    prompt = f"""Based on the following search results, please provide a recipe.
Search results:
{search_results}

User's request: {dish_query}
"""

    llm_with_tools = llm.bind_tools([Recipe])
    response = llm_with_tools.invoke(prompt)
    state["messages"].append(response)
    return state

def inventory_manager(state: AgentState):
    """Checks the inventory for the ingredients in the recipe."""
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

def recipe_scaler(state: AgentState):
    """Scales the recipe based on the number of servings."""
    recipe_tool_call = state["messages"][-1].tool_calls[0]
    recipe = recipe_tool_call["args"]
    servings = state["servings"]

    # Create a new dictionary for the scaled recipe
    scaled_recipe = recipe.copy()
    scaled_ingredients = {}

    for ingredient, quantity in recipe["ingredients"].items():
        # Extract the numerical part of the quantity
        parts = quantity.split()
        if len(parts) > 0 and parts[0].isdigit():
            amount = int(parts[0])
            scaled_amount = amount * servings
            scaled_ingredients[ingredient] = f"{scaled_amount} {' '.join(parts[1:])}"
        else:
            scaled_ingredients[ingredient] = quantity # Keep as is if no numerical value

    scaled_recipe["ingredients"] = scaled_ingredients
    state["messages"].append(ToolMessage(tool_call_id=recipe_tool_call["id"], content=json.dumps({"scaled_recipe": scaled_recipe})))
    return state


def shopping_list_manager(state: AgentState):
    """Creates a shopping list of missing ingredients."""
    last_message = state["messages"][-1]
    missing_items_data = json.loads(last_message.content)
    missing_items = missing_items_data["missing_items"]

    llm_with_tools = llm.bind_tools([ShoppingList])
    prompt = f"Please format the following list of missing ingredients into a structured shopping list with quantities and units. For each item, separate the quantity and the unit. If you can't determine a quantity or unit, you can make a reasonable assumption or leave it as a string. Missing items: {json.dumps(missing_items)}"
    response = llm_with_tools.invoke(prompt)
    state["messages"].append(response)

    shopping_list_tool_call = response.tool_calls[0]
    formatted_shopping_list = shopping_list_tool_call["args"]["shopping_list"]

    with open("shopping_list.json", "w") as f:
        json.dump(formatted_shopping_list, f, indent=4)

    state["shopping_list"] = formatted_shopping_list
    return state

def printer(state: AgentState):
    """Prints the final output."""
    if state.get("shopping_list"):
        print("\nShopping list created in shopping_list.json")
        print(json.dumps(state["shopping_list"], indent=4))
    else:
        last_message = state["messages"][-1]
        recipe_data = json.loads(last_message.content)
        print("\nRecipe:")
        print(json.dumps(recipe_data.get("scaled_recipe", recipe_data.get("recipe")), indent=4))

# ------------------ GRAPH ------------------

workflow = StateGraph(AgentState)

workflow.add_node("recipe_fetcher", recipe_fetcher)
workflow.add_node("inventory_manager", inventory_manager)
workflow.add_node("recipe_scaler", recipe_scaler)
workflow.add_node("shopping_list_manager", shopping_list_manager)
workflow.add_node("printer", printer)


workflow.set_entry_point("recipe_fetcher")

workflow.add_edge("recipe_fetcher", "inventory_manager")
workflow.add_edge("shopping_list_manager", "printer")
workflow.add_edge("recipe_scaler", "printer")
workflow.add_edge("printer", END)


def should_continue(state: AgentState):
    if "missing_items" in state["messages"][-1].content:
        return "shopping_list_manager"
    else:
        return "recipe_scaler"

workflow.add_conditional_edges(
    "inventory_manager",
    should_continue,
    {"shopping_list_manager": "shopping_list_manager", "recipe_scaler": "recipe_scaler"}
)

# ------------------ MAIN ------------------

def main():
    """Main function to run the foodie agent."""
    with SqliteSaver.from_conn_string(":memory:") as memory:
        app = workflow.compile(checkpointer=memory)
        mermaid_code = app.get_graph().draw_mermaid()
        draw_mermaid_png(mermaid_syntax=mermaid_code, output_file_path="graph.png")

        config = {"configurable": {"thread_id": "1"}}

        dish = input("What dish would you like to cook? ")
        servings = int(input("How many servings? "))

        initial_state = {
            "messages": [f"Prepare a recipe for {dish}."],
            "servings": servings
        }

        for event in app.stream(initial_state, config=config):
            for key, value in event.items():
                if key != "__end__":
                    print(f"--- {key} ---")
                    print(value)


if __name__ == "__main__":
    main()


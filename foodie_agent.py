

import os
import json
from typing import Annotated, List, TypedDict

from langchain_core.messages import BaseMessage, ToolMessage
from pydantic import BaseModel, Field
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


# ------------------ STATE ------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    inventory: dict
    servings: int

# ------------------ NODES ------------------

def recipe_fetcher(state: AgentState):
    """Fetches a recipe based on the user's request."""
    search = DuckDuckGoSearchRun()
    dish_query = state["messages"][0]
    search_results = search.run(f"recipe for {dish_query} for 2 serving")

    prompt = f"""
        You are a culinary assistant. Your task is to output a standardized recipe JSON with normalized units.

        - Normalize all measurements to the following units wherever applicable:
        - "tsp" for teaspoons (e.g., "tsp", "teaspoon", "tsp.")
        - "tbsp" for tablespoons (e.g., "tbsp", "tablespoon", "tbsp.")
        - "g" for grams
        - "kg" for kilograms
        - "ml" for milliliters
        - "l" for liters
        - "cup" for cups
        - Keep subjective quantities as-is (e.g., "pinch", "to taste", "bunch")

        - If you encounter synonyms or abbreviations, convert them to the standardized units above.

        - Ingredients should be presented as a JSON dictionary with ingredient names as keys and each value an object with "quantity" (string) and "unit" (string).

        - Example input variations:
        - "1 tsp", "1 teaspoon", "1 tsp." => standardize as {{"quantity": "1", "unit": "tsp"}}
        - "2 tablespoons", "2 tbsp" => standardize as {{"quantity": "2", "unit": "tbsp"}}

        - The output must be a valid JSON object containing "ingredients" and "instructions" fields.

        ---

        Based on the following search results, please provide a recipe for 2 servings.

        Search results:
        {search_results}

        User's request:
        {dish_query}

        Give detailed instructions.
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

    # Units that probably shouldn't be scaled but just copied (e.g. subjective units)
    non_scalable_units = {"to taste", "", "bunch", "medium", "pinch"}

    for ingredient, info in recipe["ingredients"].items():
        qty = info.get("quantity")
        unit = info.get("unit", "").lower()

        # Check if quantity is numeric
        try:
            amount = float(qty)
        except (ValueError, TypeError):
            # Non-numeric quantity
            scaled_ingredients[ingredient] = info
            continue

        # Decide if we should scale this ingredient quantity
        if unit in non_scalable_units:
            # Do not scale subjective quantities, keep as is
            scaled_amount = amount
        else:
            scaled_amount = amount * servings

        # Optionally: check inventory and generate warning if insufficient
        inv_item = inventory.get(ingredient)
        if inv_item:
            inv_quantity = inv_item.get("quantity", 0)
            inv_unit = inv_item.get("unit", "").lower()

            # Basic check if units match before comparing
            if unit == inv_unit and isinstance(inv_quantity, (int, float)):
                if scaled_amount > inv_quantity:
                    print(f"Warning: Insufficient '{ingredient}' in inventory for {servings} servings.")
            else:
                # Units don't match, skipping inventory quantity check here
                pass
        else:
            # Ingredient not found in inventory - optional warning
            print(f"Warning: Ingredient '{ingredient}' not found in inventory.")

        scaled_ingredients[ingredient] = {
            "quantity": str(scaled_amount) if scaled_amount % 1 else str(int(scaled_amount)),
            "unit": unit
        }

    scaled_recipe["ingredients"] = scaled_ingredients

    # Append new scaled recipe as a ToolMessage
    state["messages"].append(
        ToolMessage(
            tool_call_id=recipe_tool_call["id"],
            content=json.dumps({"scaled_recipe": scaled_recipe})
        )
    )
    return state


def printer(state: AgentState):
    """Prints the final output."""
    last_message = state["messages"][-1]
    recipe_data = json.loads(last_message.content)
    print("\nRecipe:")
    print(json.dumps(recipe_data.get("scaled_recipe", recipe_data.get("recipe")), indent=4))

# ------------------ GRAPH ------------------

workflow = StateGraph(AgentState)

workflow.add_node("recipe_fetcher", recipe_fetcher)
workflow.add_node("inventory_manager", inventory_manager)
workflow.add_node("recipe_scaler", recipe_scaler)
workflow.add_node("printer", printer)


workflow.set_entry_point("recipe_fetcher")

workflow.add_edge("recipe_fetcher", "inventory_manager")
workflow.add_edge("inventory_manager", "recipe_scaler")
workflow.add_edge("recipe_scaler", "printer")
workflow.add_edge("printer", END)

# ------------------ MAIN ------------------

def main():
    """Main function to run the foodie agent."""
    with SqliteSaver.from_conn_string(":memory:") as memory:
        app = workflow.compile(checkpointer=memory)
        mermaid_code = app.get_graph().draw_mermaid()
        draw_mermaid_png(mermaid_syntax=mermaid_code, output_file_path="graph.png")

        config = {"configurable": {"thread_id": "1"}}

        dish = "palak paneer"
        servings = "6"

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


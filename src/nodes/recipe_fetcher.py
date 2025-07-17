from langchain_community.tools import DuckDuckGoSearchRun
from src.state import AgentState
from src.config import llm
from src.models import Recipe

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

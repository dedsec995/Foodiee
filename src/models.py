from pydantic import BaseModel, Field
from typing import List

class Recipe(BaseModel):
    """Represents a recipe with ingredients and instructions."""
    recipe_name: str = Field(description="The name of the recipe.")
    ingredients: dict = Field(description="A dictionary of ingredients and their quantities.")
    instructions: List[str] = Field(description="A list of instructions for the recipe.")

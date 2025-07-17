import os
import time
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.runnables.graph_mermaid import draw_mermaid_png
from judgeval.common.tracer import Tracer
from judgeval.integrations.langgraph import JudgevalCallbackHandler
from src.graph import workflow
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.text import Text

load_dotenv()

# ----------------- Let's Judge -------------
judgment = Tracer(project_name="foodiee")
handler = JudgevalCallbackHandler(judgment)

def main():
    """ The Main Function that initialize and Invokes the Graph """
    console = Console()

    console.print(Panel(Text("Welcome to Foodie!", justify="center", style="bold green"), title="[bold]Foodie AI Assistant[/bold]", border_style="green"))

    with console.status("[bold green]Warming up the kitchen...", spinner="dots") as status:
        time.sleep(2)
        status.update(spinner="bouncingBar", status="[bold cyan]Checking the pantry...")
        time.sleep(2)
        status.update(spinner="clock", status="[bold yellow]Sharpening the knives...")
        time.sleep(2)

    dish = Prompt.ask("[bold cyan]What dish would you like to cook today? :fork_and_knife:")
    servings = Prompt.ask("[bold cyan]How many servings? :shallow_pan_of_food:")

    config = {"configurable": {"thread_id": "1"}, "callbacks": [handler]}
    with SqliteSaver.from_conn_string(":memory:") as memory:
        app = workflow.compile(checkpointer=memory)

        initial_state = {
            "messages": [f"Prepare a recipe for {dish}."],
            "servings": servings
        }

        with console.status("[bold green]Cooking up your recipe...", spinner="earth"):
            final_state = app.invoke(initial_state, config=config)

    console.print("\n[bold green]Execution Details:[/bold green]")
    console.print(f"  [bold]Executed Nodes:[/bold] {handler.executed_nodes}")


if __name__ == "__main__":
    main()

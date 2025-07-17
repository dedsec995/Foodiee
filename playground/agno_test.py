import os
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools

from judgeval.tracer import Tracer, wrap

# Load environment variables (for GROQ_API_KEY)
load_dotenv()

judgment = Tracer(project_name="tripAi")

# Initialize the Agno agent with Groq as the LLM provider
agent = Agent(
    name="Web Search Agent",
    role="Search the web for financial information",
    model=Groq(id="llama-3.3-70b-versatile"),  # Use the Groq LLM
    tools=[DuckDuckGoTools()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)

# Wrap the agent with judgeval for tracing and evaluation
agent = wrap(agent)

@judgment.observe  # Decorator to trace this function's agent runs
def run_agent(query):
    response = agent.run(query)
    print(response)
    return response

run_agent("What are the latest market trends for AI semiconductor companies?")

from judgeval.tracer import Tracer, wrap
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv
import os
load_dotenv()


client = wrap(Groq(api_key=os.environ.get("GROQ_API_KEY"),))  # tracks all LLM calls
judgment = Tracer(project_name="tripAi")

@judgment.observe(span_type="tool")
def format_question(question: str) -> str:
    # dummy tool
    return f"Question : {question}"

@judgment.observe(span_type="function")
def run_agent(prompt: str) -> str:
    task = format_question(prompt)
    response = client.chat.completions.create(
        model="qwen/qwen3-32b",
        messages=[{"role": "user", "content": task}]
    )
    return response.choices[0].message.content

run_agent("What is the capital of the Australia?")
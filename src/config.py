import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(temperature=0.8, model_name="llama3-70b-8192", api_key=GROQ_API_KEY)

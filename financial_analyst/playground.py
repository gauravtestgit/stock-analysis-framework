from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo

import os
import phi
from phi.playground import Playground, serve_playground_app

from dotenv import load_dotenv
load_dotenv()

phi.api = os.getenv("PHI_API_KEY")
phi_data_api_key = os.getenv("PHI_DATA_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found. Please restart your terminal/IDE after setting with setx.")

# Web Search Agent

web_search_agent = Agent(
    name="Web Search Agent",
    role="search the web for information",
    model=Groq(id="llama-3.1-8b-instant", api_key=groq_api_key),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True
)

# Financial Agent

financial_agent = Agent(
    name="Finance AI Agent",
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    model=Groq(id="llama-3.1-8b-instant", api_key=groq_api_key),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    instructions=["Format your response using markdown and use tables to display data where possible."],
    show_tool_calls=True,
    markdown=True    
)

app = Playground(
    agents=[
        web_search_agent,
        financial_agent
    ]
).get_app()

if __name__ == "__main__":
    serve_playground_app("playground:app", reload=True)
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from cdpHandler import getWallet

load_dotenv()

model = ChatAnthropic(model="claude-3-5-sonnet-20240620")

tools = [TavilySearchResults(max_results=2)]

wallet = getWallet()

print(wallet.default_address)

graph = create_react_agent(model, tools)

import logging

from fastapi import FastAPI
from agent import graph
from pydantic import BaseModel

from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

class Request(BaseModel):
    requestRef: str
    threadID: str


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/human")
async def read_human(request: Request):
    config = RunnableConfig(configurable= {"thread_id": request.threadID})
    inputs = {"messages": [("human", request.requestRef)]}
    final_result = {"messages":["none"]}
    async for chunk in graph.astream(inputs, config, stream_mode="values"):
        final_result = chunk
        logger.info(final_result)
    return final_result["messages"][-1]

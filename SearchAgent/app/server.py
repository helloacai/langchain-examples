from typing import Union
import logging

from fastapi import FastAPI
from agent import graph

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

class Request(BaseModel):
    requestRef: str


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/human")
async def read_human(request: Request):
    inputs = {"messages": [("human", request.requestRef)]}
    async for chunk in graph.astream(inputs, stream_mode="values"):
        final_result = chunk
        logger.info(final_result)
    return final_result["messages"][-1]
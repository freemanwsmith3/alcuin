from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_current_user
from app.graph import builder, generator, querier

router = APIRouter(prefix="/graph", tags=["graph"])


class GenerateRequest(BaseModel):
    prompt: str


class QueryRequest(BaseModel):
    question: str


@router.post("/generate")
async def generate_data(body: GenerateRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        schema = generator.generate(body.prompt, user.id)
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build")
async def build_graph(user: CurrentUser = Depends(get_current_user)):
    schema = generator.load(user.id)
    if schema is None:
        raise HTTPException(status_code=404, detail="No data found. Generate data first.")
    try:
        graph = builder.build(user.id, schema)
        return {"graph": graph, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_graph(user: CurrentUser = Depends(get_current_user)):
    schema = generator.load(user.id)
    if schema is None:
        return {"graph": None, "schema": None}
    graph = builder.load_graph(user.id, schema)
    return {"graph": graph, "schema": schema}


@router.post("/query")
async def query_graph(body: QueryRequest, user: CurrentUser = Depends(get_current_user)):
    schema = generator.load(user.id)
    if schema is None:
        raise HTTPException(status_code=404, detail="No graph found. Generate and build first.")
    answer = querier.query(body.question, user.id, schema)
    if answer is None:
        raise HTTPException(status_code=422, detail="Could not generate a valid query for that question.")
    return {"answer": answer}

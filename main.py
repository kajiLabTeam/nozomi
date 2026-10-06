from typing import cast

from fastapi import FastAPI
from rikka.main import printname

from nozomi.adapter import RikkaAdapter
from nozomi.catalog import initial_catalog
from nozomi.models import ErrorEnvelope, PipelineCatalogEntry, PipelineSnapshot
from nozomi.registry import PipelineRegistry

app = FastAPI()
registry = PipelineRegistry(initial_catalog(), RikkaAdapter())


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/rikka")
def read_rikka(q: str = "World") -> str:
    return cast(str, printname(q))


@app.get("/pipelines", response_model=list[PipelineCatalogEntry])
def list_pipelines() -> list[PipelineCatalogEntry]:
    return list(registry.catalog())


@app.get(
    "/internal/pipelines/{pipeline_id}",
    response_model=PipelineSnapshot,
    responses={404: {"model": ErrorEnvelope}},
)
def resolve_pipeline(pipeline_id: str) -> PipelineSnapshot:
    snapshot = registry.resolve(pipeline_id)
    if snapshot is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404,
            content={
                "detail": {"code": "unknown_pipeline", "message": "Unknown pipeline_id"}
            },
        )  # type: ignore[return-value]
    return snapshot

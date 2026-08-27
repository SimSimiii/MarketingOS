from fastapi import APIRouter

from app.schemas.model_catalog import ModelCatalogRead, build_catalog

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelCatalogRead)
def list_models() -> ModelCatalogRead:
    """Every model the picker can offer, and every agent one can be pinned to.

    Static for the lifetime of a build, but served rather than bundled: the
    frontend must not carry its own copy of a list the router reads, or the two
    drift and the UI starts offering models that no longer route.
    """
    return build_catalog()

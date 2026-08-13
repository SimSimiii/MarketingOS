from fastapi import APIRouter

from app.api.deps import SettingsServiceDep
from app.schemas.settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsRead)
def get_settings(service: SettingsServiceDep) -> UserSettingsRead:
    return UserSettingsRead.model_validate(service.get_settings())


@router.patch("", response_model=UserSettingsRead)
def update_settings(data: UserSettingsUpdate, service: SettingsServiceDep) -> UserSettingsRead:
    return UserSettingsRead.model_validate(service.update_settings(data))

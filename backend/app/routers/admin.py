from fastapi import APIRouter, Depends

from app.routers import (
    admin_content,
    admin_diagnostic,
    admin_drafts,
    admin_gamification,
    admin_generation,
    admin_markets,
    admin_media,
    admin_settings,
    admin_translations,
)
from app.routers.admin_auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])
router.include_router(admin_content.router)
router.include_router(admin_generation.router)
router.include_router(admin_drafts.router)
router.include_router(admin_markets.router)
router.include_router(admin_translations.router)
router.include_router(admin_gamification.router)
router.include_router(admin_settings.router)
router.include_router(admin_media.router)
router.include_router(admin_diagnostic.router)

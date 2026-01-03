from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.champions import router as champions_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.configs import router as configs_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(champions_router, prefix="/champions", tags=["champions"])
router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
router.include_router(drafts_router, prefix="/drafts", tags=["drafts"])
router.include_router(configs_router,  prefix="/configs", tags=["configs"])

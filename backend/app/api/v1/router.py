from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, profile, repositories

api_router = APIRouter()

# Active endpoints
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(health.router, prefix="/v1", tags=["Health (v1)"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(auth.router, prefix="/v1/auth", tags=["Authentication (v1)"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(repositories.router, prefix="/v1/repositories", tags=["Repositories (v1)"])
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
api_router.include_router(profile.router, prefix="/v1/profile", tags=["Profile (v1)"])

# ==============================================================================
# Planned Future Endpoints (To be implemented in subsequent phases)
# ==============================================================================
# - /api/repositories                   (Repository ingestion and listing)
# - /api/repositories/{id}              (Repository detail, files, architecture)
# - /api/repositories/{id}/issues       (Repository issue list and skill matching)
# - /api/repositories/{id}/analysis     (Deep repository analysis)
# - /api/repositories/{id}/chat         (RAG repository Q&A chat)
# - /api/issues/{id}                    (Individual issue details & contribution guide)
# - /api/users                          (User account management)
# - /api/users/{id}/skills              (Developer skill profiling)

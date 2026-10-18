from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings

from backend.app.routers.recommendations import router as recommendations_router
from backend.app.routers.assistant import router as assistant_router
from backend.app.routers.pantry import router as pantry_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.substitutions import router as substitutions_router
from backend.app.routers.safety import router as safety_router
from backend.app.routers.shopping import router as shopping_router
from backend.app.routers.sandbox import router as sandbox_router
from backend.app.routers.recipes import router as recipes_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Pantry Recipe Assistant — RAG + 5 Novelty Dimensions",
    version="2.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes at both /api and /api/v1 for clean access
routers = [
    recommendations_router,
    assistant_router,
    pantry_router,
    analytics_router,
    substitutions_router,
    safety_router,
    shopping_router,
    sandbox_router,
    recipes_router,
]

for r in routers:
    app.include_router(r, prefix="/api")
    app.include_router(r, prefix=settings.API_V1_STR)

# Also expose direct POST /api/recommend alias for spec compatibility
from backend.app.models.recommendation import PantryRequest, RecommendationResponse
from backend.app.services.recommendation_service import recommendation_service

@app.post("/api/recommend", response_model=RecommendationResponse, tags=["recommendations"])
@app.post("/api/v1/recommend", response_model=RecommendationResponse, tags=["recommendations"])
def recommend_alias(request: PantryRequest):
    return recommendation_service.get_recommendations(request)


@app.get("/")
def read_root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "version": "2.0.0",
        "description": "RAG-Enhanced Culinary Intelligence with 5 Novelty Modules (Graph Substitutions, Hard Safety Lock, Food Waste Optimizer, Micro-Shopping, Interactive Sandbox)",
        "endpoints": {
            "pantry": "/api/pantry",
            "recommendations": "/api/recommendations",
            "recommend": "/api/recommend",
            "substitutions": "/api/substitutions",
            "safety_check": "/api/safety/check",
            "shopping_optimize": "/api/shopping/optimize",
            "sandbox_simulate": "/api/sandbox/simulate",
            "recipes": "/api/recipes/{id}",
            "assistant_ask": "/api/assistant/ask",
            "sustainability_analytics": "/api/analytics/sustainability",
            "health": "/health",
        },
    }

@app.get("/health")
def health_check():
    parquet_exists = settings.PARQUET_PATH.exists()
    sqlite_exists = settings.SQLITE_INDEX_PATH.exists()
    return {
        "status": "healthy",
        "data_ready": {
            "recipes_parquet": parquet_exists,
            "ingredient_index_sqlite": sqlite_exists,
        },
    }

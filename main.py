from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import models
from database import engine

from routers import auth, courses, discussions, leaderboard, quizzes, profile, analytics, enrollment, meetings, materials, notifications

models.Base.metadata.create_all(bind=engine)

# Allowed frontend origins for CORS
CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)

app = FastAPI(title="AI Learning Hub API")


class EnsureCORSHeadersMiddleware(BaseHTTPMiddleware):
    """Add CORS headers to every response so browser never blocks (e.g. on errors)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin in CORS_ORIGINS:
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
        response.headers.setdefault("Access-Control-Allow-Headers", "*")
        return response


# Add our middleware first so it runs last on response and can add headers if missing
app.add_middleware(EnsureCORSHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(discussions.router)
app.include_router(leaderboard.router)
app.include_router(quizzes.router)
app.include_router(profile.router)
app.include_router(analytics.router)
app.include_router(enrollment.router)
app.include_router(meetings.router)
app.include_router(materials.router)
app.include_router(notifications.router)

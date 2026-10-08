from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router


def create_app() -> FastAPI:
    app = FastAPI(title="Sanad", description="Bilingual document assistant with citations")

    # Any site may call the API (the embeddable widget runs on client sites).
    # No cookies are used: access is by workspace key, so credentials stay off.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

"""Backward-compatible entrypoint for MuseWave backend."""

from server import app


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=os.environ.get("ENV") != "production")

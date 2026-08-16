# Wiring only: load config, create the FastAPI app, mount routers. No business logic here.
from fastapi import FastAPI

app = FastAPI(title="kyomei-api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

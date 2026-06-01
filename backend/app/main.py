from fastapi import FastAPI

app = FastAPI(
    title="MarketAtlas",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "project": "MarketAtlas",
        "status": "running"
    }
"""后端启动入口：uvicorn app.main:app"""
from app.main import app

if __name__ == "__main__":
    import uvicorn

    from app.config import Settings

    s = Settings()
    uvicorn.run("app.main:app", host=s.HOST, port=s.PORT, reload=False)

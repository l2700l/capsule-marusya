import uvicorn
from config.settings import HOST, PORT

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=HOST,
        port=PORT,
        reload=True,
    )
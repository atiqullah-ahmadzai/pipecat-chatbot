import argparse
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
import models
from database import engine, SessionLocal
import routes
from typing import Any, Dict
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams
from contextlib import asynccontextmanager
import aiohttp
import subprocess

load_dotenv(override=True)
bot_procs = {}
daily_helpers = {}

def cleanup():
    for entry in bot_procs.values():
        proc = entry[0]
        proc.terminate()
        proc.wait()
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )
    yield
    await aiohttp_session.close()
    cleanup()
    
    
# Init database
app = FastAPI(lifespan=lifespan)
models.Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Middleware
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes.router)


async def create_room_and_token() -> tuple[str, str]:
    room = await daily_helpers["rest"].create_room(DailyRoomParams())
    if not room.url:
        raise HTTPException(status_code=500, detail="Failed to create room")

    token = await daily_helpers["rest"].get_token(room.url)
    if not token:
        raise HTTPException(status_code=500, detail=f"Failed to get token for room: {room.url}")

    return room.url, token


@app.post("/connect/{id}")
async def bot_connect(request: Request, id: int) -> Dict[Any, Any]:
    from crud import DatabaseHelper
    db = DatabaseHelper()
    website = db.get_single(models.Website, id)
    room_url, token = await create_room_and_token()
    python_path = os.getenv("PYTHON_PATH", "python3")
    try:
        bot_file = "voice_bot"
        proc = subprocess.Popen(
            [f"{python_path} -m {bot_file} -u {room_url} -t {token} -l {website.url} -i {id}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")
    return {"room_url": room_url, "token": token}



if __name__ == "__main__":
    import uvicorn

    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "8001"))

    parser = argparse.ArgumentParser(description="Daily Travel Companion FastAPI server")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    parser.add_argument("--port", type=int, default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Reload code on change")

    config = parser.parse_args()

    uvicorn.run(
        "server:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
    )
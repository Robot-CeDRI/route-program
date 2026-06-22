import argparse
import uvicorn

from fastapi import FastAPI, HTTPException

from config import settings
from api import data_receiver

from database import repository as db

from schemas.data_receive import ModelDataValidator, ModelDataResponse
from tasks.scheduler import scheduler, setup_scheduler

import os

from core import messages as m
from core.log import log, setVerbose

active_models = {}
active_sessions = {}

# ==========================================
#       MAIN APPLICATION
# ==========================================


async def lifespan(app: FastAPI):
    setVerbose(settings[m.VERBOSE])
    log(f"starting with Verbose Mode ON...")
    log(f"[setting] Program:\t\t 0.0.0.0:{settings[m.PORT]}")
    log(f"[setting] IA Manager:\t {settings[m.IPIA]}:{settings[m.PORTIA]}")
    log("Starting Program...",0)

    if not db.start():
        log("Failed to initialize the database. Exiting.", 3)
        os._exit(1)

    setup_scheduler()
    scheduler.start()    
    
    yield
    log("Stopping Program...", 0)

app = FastAPI(
    title="CEDRI Route Manager",
    description="REST API for the CEDRI Route Manager from IPB",
    version="2.0.0",
    lifespan=lifespan
)

# ==========================================
#       ROTAS REST
# ==========================================

@app.get("/api/echo")
async def echo_route():
    return {"message": "[S] Ai manager loaded."}

@app.post("/api/models/send-data", status_code=200, response_model=ModelDataResponse)
async def send_data(payload: ModelDataValidator):
    """Model data endpoint, receives the model data and accumulates it for further processing."""
    result = data_receiver.run(payload.model_dump())
    return result

# ==========================================
#       INICIALIZAÇÃO E ARGPARSE
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CEDRI AI Manager Startup Script")
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Activate detailed loggings.")
    parser.add_argument("--port", type=int, help="Server port")
    parser.add_argument("--ipia", type=str, help="Communication IP with the AI")
    parser.add_argument("--portia", type=int, help="Communication port with the AI")
    parser.add_argument("--new", action="store_true", help="Create a new model model_token, ignoring existing ones.")

    args = parser.parse_args()

    if args.verbose:
        settings[m.VERBOSE] = True
    else:
        settings[m.VERBOSE] = False

    if args.new:
        settings[m.NEW] = True
    else:
        settings[m.NEW] = False

    if args.port is not None:
        settings[m.PORT] = args.port
    if args.ipia is not None:
        settings[m.IPIA] = args.ipia
    if args.portia is not None:
        settings[m.PORTIA] = args.portia

    
    uvicorn.run(app, host="0.0.0.0", port=int(settings[m.PORT]))
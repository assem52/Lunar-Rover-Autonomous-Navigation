import threading
import webbrowser
import time
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server import settings
from server.api.ws import router as ws_router
from server.core.container import manager
from server.logger import setup_logging

app = FastAPI()

app.include_router(ws_router)
app.mount('/static', StaticFiles(directory=settings.STATIC_DIR, html=True), name='static')


@app.get('/')
def root():
    return RedirectResponse(url='/static/index.html')


@app.get('/health')
def health():
    return {
        'status': 'ok',
        'mode': manager.sim.get('mode', 'idle'),
        'clients': len(manager.clients),
    }


@app.get('/api/config')
def api_config():
    """Expose server-side constants to the frontend (single source of truth)."""
    return {
        'grid_size':   settings.GRID_SIZE,
        'num_craters': settings.NUM_CRATERS,
        'num_rocks':   settings.NUM_ROCKS,
    }


@app.get('/state')
def state():
    return manager.static_payload()



@app.on_event('startup')
async def on_startup():
    setup_logging()
    if os.getenv('DISABLE_SERVER_BROWSER_OPEN') == '1':
        return

    def _open():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:8000')

    threading.Thread(target=_open, daemon=True).start()

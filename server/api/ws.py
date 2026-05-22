import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server import settings
from server.core.container import manager

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Command handlers — add new actions here without touching ws_endpoint()
# ---------------------------------------------------------------------------

async def _handle_train(cmd):
    await manager.start_training()

async def _handle_train_new_map(cmd):
    exploration = cmd.get('exploration')
    exploitation = cmd.get('exploitation')
    map_name = await manager.train_on_new_map(exploration=exploration, exploitation=exploitation)
    await manager.emit_event('info', message=f"Training started on new map: {map_name}")

async def _handle_run(cmd):
    await manager.start_run()

async def _handle_run_trained_map(cmd):
    name = cmd.get('name')
    ok, err = await manager.run_trained_map(name)
    if not ok:
        await manager.emit_event('error', message=err)

async def _handle_run_trained_model(cmd):
    name = cmd.get('name')
    ok, err = await manager.run_trained_model(name)
    if not ok:
        await manager.emit_event('error', message=err)

async def _handle_stop(cmd):
    await manager.stop_simulation()

async def _handle_stop_and_save(cmd):
    name = cmd.get('name')
    if not name:
        await manager.emit_event('error', message='Model name cannot be empty.')
        return
    saved_name = await manager.stop_and_save(name)
    await manager.emit_event('saved', model_name=saved_name, models=manager.sim.get('models', []))

async def _handle_pause(cmd):
    await manager.pause_simulation()

async def _handle_resume(cmd):
    await manager.resume_simulation()

async def _handle_save(cmd):
    name = cmd.get('name', manager.sim['model_name'])
    if not name:
        await manager.emit_event('error', message='Model name cannot be empty.')
        return
    saved_name = manager.save_model(name)
    await manager.emit_event(
        'saved',
        trained_eps=manager.sim['trained_eps'],
        models=manager.sim.get('models', []),
        model_name=saved_name,
    )

async def _handle_load_model(cmd):
    name = cmd.get('name')
    if not name:
        await manager.emit_event('error', message='Select a model to load.')
        return
    ok, err = await manager.load_model(name)
    if not ok:
        await manager.emit_event('error', message=err)
    else:
        await manager.broadcast(manager.static_payload())

async def _handle_new_map(cmd):
    manager.cancel_task()
    map_name = await manager.create_new_map()
    await manager.broadcast(manager.static_payload())
    await manager.emit_event('info', message=f"New map created: {map_name}")

async def _handle_load_map(cmd):
    name = cmd.get('name')
    if not name:
        await manager.emit_event('error', message='Select a map to load.')
        return
    ok = await manager.load_map(name)
    if not ok:
        await manager.emit_event('error', message=f"Map '{name}' not found.")
    else:
        await manager.broadcast(manager.static_payload())

async def _handle_set_speed(cmd):
    try:
        actual = manager.set_speed(float(cmd.get('value', settings.DEFAULT_SPEED)))
        await manager.emit_event('info', message=f'Speed set to {actual:.2f}s')
    except Exception:
        await manager.emit_event('error', message='Invalid speed value.')

async def _handle_set_personality(cmd):
    name = cmd.get('name')
    if not name:
        await manager.emit_event('error', message='Personality name cannot be empty.')
        return
    if manager.set_personality(name):
        await manager.broadcast(manager.static_payload())
        await manager.emit_event('info', message=f"Personality changed to: {name.capitalize()}")
    else:
        await manager.emit_event('error', message=f"Unknown personality: {name}")


# Canonical action name → handler (aliases handled separately below)
_HANDLERS = {
    'train':           _handle_train,
    'train_new_map':   _handle_train_new_map,
    'start_training':  _handle_train,
    'run':             _handle_run,
    'start_run':       _handle_run,
    'run_trained_map': _handle_run_trained_map,
    'run_trained_model': _handle_run_trained_model,
    'stop':            _handle_stop,
    'stop_and_save':   _handle_stop_and_save,
    'stop_simulation': _handle_stop,
    'end':             _handle_stop,
    'pause':           _handle_pause,
    'resume':          _handle_resume,
    'save':            _handle_save,
    'load_model':      _handle_load_model,
    'new_map':         _handle_new_map,
    'load_map':        _handle_load_map,
    'set_speed':       _handle_set_speed,
    'set_personality': _handle_set_personality,
}

# Actions that must not fire in the first 1.5 s after connection
_AUTOSTART_GUARD = frozenset({'train', 'start_training', 'run', 'start_run'})


@router.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    manager.clients.append(ws)

    manager.sim['mode'] = 'idle'
    connection_time = asyncio.get_event_loop().time()
    await manager.sync_state_initial()
    await ws.send_text(json.dumps(manager.static_payload()))

    try:
        while True:
            raw = await ws.receive_text()
            cmd = json.loads(raw)
            action = cmd.get('action')
            if not action:
                continue

            log.debug("WebSocket action received: %s", action)

            # Safety guard: ignore auto-start commands right after connection
            if action in _AUTOSTART_GUARD:
                if asyncio.get_event_loop().time() - connection_time < 1.5:
                    log.warning("Blocked potential auto-start action: %s", action)
                    continue

            handler = _HANDLERS.get(action)
            if handler:
                await handler(cmd)
            else:
                await manager.emit_event('error', message=f"Unknown action: {action}")

    except WebSocketDisconnect:
        if ws in manager.clients:
            manager.clients.remove(ws)
        if len(manager.clients) == 0:
            if manager.sim['mode'] in ('training', 'running'):
                await manager.pause_simulation()



import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server import settings
from server.core.container import manager

router = APIRouter()


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
            if action:
                print(f"[*] WebSocket Action Received: {action}")

            # Safety check: Ignore auto-commands from browser cache in the first 1.5s
            if action in ('train', 'start_training', 'run', 'start_run'):
                if asyncio.get_event_loop().time() - connection_time < 1.5:
                    print(f"[!] Blocked potential auto-start action: {action}")
                    continue

            if action == 'start_training' or action == 'train':
                await manager.start_training()

            elif action == 'start_run' or action == 'run':
                await manager.start_run()

            elif action == 'stop_simulation' or action == 'end' or action == 'stop':
                await manager.stop_simulation()

            elif action == 'pause':
                await manager.pause_simulation()

            elif action == 'resume':
                await manager.resume_simulation()

            elif action == 'stop': # Fallback
                await manager.stop_simulation()

            elif action == 'save':
                name = cmd.get('name', manager.sim['model_name'])
                if not name:
                    await manager.emit_event('error', message='Model name cannot be empty.')
                    continue
                saved_name = manager.save_model(name)
                await manager.emit_event('saved', trained_eps=manager.sim['trained_eps'], models=manager.sim.get('models', []), model_name=saved_name)

            elif action == 'load_model':
                name = cmd.get('name')
                if not name:
                    await manager.emit_event('error', message='Select a model to load.')
                    continue
                ok, err = await manager.load_model(name)
                if not ok:
                    await manager.emit_event('error', message=err)
                else:
                    await manager.broadcast(manager.static_payload())

            elif action == 'new_map':
                manager.cancel_task()
                map_name = await manager.create_new_map()
                await manager.broadcast(manager.static_payload())
                await manager.emit_event('info', message=f"New map created: {map_name}")

            elif action == 'load_map':
                name = cmd.get('name')
                if not name:
                    await manager.emit_event('error', message='Select a map to load.')
                    continue
                ok = await manager.load_map(name)
                if not ok:
                    await manager.emit_event('error', message=f"Map '{name}' not found.")
                else:
                    await manager.broadcast(manager.static_payload())

            elif action == 'set_speed':
                try:
                    actual = manager.set_speed(float(cmd.get('value', settings.DEFAULT_SPEED)))
                    await manager.emit_event('info', message=f'Speed set to {actual:.2f}s')
                except Exception:
                    await manager.emit_event('error', message='Invalid speed value.')

            elif action == 'set_personality':
                name = cmd.get('name')
                if not name:
                    await manager.emit_event('error', message='Personality name cannot be empty.')
                    continue
                if manager.set_personality(name):
                    await manager.broadcast(manager.static_payload())
                    await manager.emit_event('info', message=f"Personality changed to: {name.capitalize()}")
                else:
                    await manager.emit_event('error', message=f"Unknown personality: {name}")

            else:
                await manager.emit_event('error', message=f"Unknown action: {action}")

    except WebSocketDisconnect:
        if ws in manager.clients:
            manager.clients.remove(ws)
        if len(manager.clients) == 0:
            if manager.sim['mode'] in ('training', 'running'):
                await manager.pause_simulation()

import asyncio
import os
import time
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from ai import QLearningAgent
from envs.lunar_rover import LunarRoverEnv
from server import settings
from server.core.stores import MapStore, ModelStore
from server.core.utils import extract_terrain, json_text
from server.core.validation import clamp_speed


class SimulationManager:
    def __init__(self) -> None:
        self.env = LunarRoverEnv(size=settings.GRID_SIZE, num_craters=settings.NUM_CRATERS, num_rocks=settings.NUM_ROCKS)
        self.agent = QLearningAgent(
            action_size=self.env.action_space.n,
            personality=settings.DEFAULT_PERSONALITY if hasattr(settings, 'DEFAULT_PERSONALITY') else "explorer"
        )

        self.model_store = ModelStore(settings.MODELS_DIR)
        self.map_store = MapStore(settings.MAPS_DIR)

        self.sim = {
            'mode': 'idle',
            'episode': 0,
            'step': 0,
            'total_reward': 0.0,
            'epsilon': self.agent.epsilon,
            'rover_pos': self.env._start_location.tolist(),
            'target_pos': self.env._target_location.tolist(),
            'craters': [],
            'rocks': [],
            'speed': settings.DEFAULT_SPEED,
            'trained_eps': 0,
            'last_outcome': '',
            'model_name': settings.DEFAULT_MODEL_NAME,
            'personality': self.agent.personality_name,
            'available_personalities': list(QLearningAgent.PERSONALITIES.keys()),
            'map_name': '',
            'perf': {'ws_msgs_per_sec': 0.0, 'ws_kb_per_sec': 0.0, 'ws_avg_msg_bytes': 0.0},
        }

        # Ensure we have a valid map loaded in the environment
        map_names = self.map_store.list_names()
        if map_names:
            first_map = map_names[0]
            map_data = self.map_store.load(first_map)
            if map_data:
                self.env.set_terrain(map_data['target'], map_data['start'], map_data['grid'])
                self.sim['map_name'] = first_map
                
                # Auto-load model for this map if it exists
                model_name = f"{first_map}_model"
                path = self.model_store.path_for(model_name)
                if os.path.exists(path):
                    self.agent.load(path)
                    self.sim['model_name'] = model_name
                    print(f"[*] Auto-loaded model: {model_name}")

        self.perf = {
            'window_start': time.monotonic(),
            'window_msgs': 0,
            'window_bytes': 0,
            'last_msgs_per_sec': 0.0,
            'last_kb_per_sec': 0.0,
            'last_avg_msg_bytes': 0.0,
        }

        self.clients: list[WebSocket] = []
        self.task: asyncio.Task | None = None
        self.best_reward = -float('inf')

        if not self.map_store.list_names():
            generated_name = self._new_map_name()
            self.sim['map_name'] = self.map_store.save(generated_name, self.get_current_map_data())
        else:
            self.sim['map_name'] = self.map_store.list_names()[0]

    def _new_map_name(self) -> str:
        count = len(self.map_store.list_names())
        return f"Map_{count + 1}"

    def get_current_map_data(self) -> dict[str, Any]:
        return {
            'target': self.env._target_location.tolist(),
            'start': self.env._start_location.tolist(),
            'grid': self.env.grid.tolist(),
        }

    def _refresh_catalogs(self) -> None:
        self.sim['models'] = self.model_store.list_names()
        self.sim['maps'] = self.map_store.list_names()

    async def sync_state_initial(self) -> None:
        self.env.reset()
        craters, rocks = extract_terrain(self.env.grid)
        self._refresh_catalogs()
        self.sim.update({
            'craters': craters,
            'rocks': rocks,
            'target_pos': self.env._target_location.tolist(),
            'rover_pos': self.env._start_location.tolist(),
        })

    def static_payload(self) -> dict[str, Any]:
        return {
            'mode': self.sim['mode'],
            'episode': self.sim['episode'],
            'step': self.sim['step'],
            'total_reward': self.sim['total_reward'],
            'epsilon': self.sim['epsilon'],
            'rover_pos': self.sim['rover_pos'],
            'target_pos': self.sim['target_pos'],
            'craters': self.sim['craters'],
            'rocks': self.sim['rocks'],
            'trained_eps': self.sim['trained_eps'],
            'last_outcome': self.sim['last_outcome'],
            'model_name': self.sim['model_name'],
            'personality': self.sim['personality'],
            'available_personalities': self.sim['available_personalities'],
            'map_name': self.sim.get('map_name', ''),
            'models': self.sim.get('models', []),
            'maps': self.sim.get('maps', []),
            'perf': self.sim.get('perf', {}),
        }

    def step_payload(self) -> dict[str, Any]:
        return {
            'mode': self.sim['mode'],
            'episode': self.sim['episode'],
            'step': self.sim['step'],
            'total_reward': self.sim['total_reward'],
            'epsilon': self.sim['epsilon'],
            'rover_pos': self.sim['rover_pos'],
            'target_pos': self.sim['target_pos'],
            'craters': self.sim['craters'],
            'rocks': self.sim['rocks'],
            'trained_eps': self.sim['trained_eps'],
            'last_outcome': self.sim['last_outcome'],
            'perf': self.sim.get('perf', {}),
        }

    async def emit_event(self, event: str, **data) -> None:
        await self.broadcast({'__event': event, **data})

    async def broadcast(self, data: dict[str, Any]) -> None:
        if not self.clients:
            return

        msg = json_text(data)
        now = time.monotonic()
        self.perf['window_msgs'] += 1
        self.perf['window_bytes'] += len(msg.encode('utf-8'))

        elapsed = now - self.perf['window_start']
        if elapsed >= 1.0:
            self.perf['last_msgs_per_sec'] = self.perf['window_msgs'] / elapsed
            self.perf['last_kb_per_sec'] = (self.perf['window_bytes'] / 1024.0) / elapsed
            self.perf['last_avg_msg_bytes'] = self.perf['window_bytes'] / self.perf['window_msgs'] if self.perf['window_msgs'] else 0.0
            self.perf['window_start'] = now
            self.perf['window_msgs'] = 0
            self.perf['window_bytes'] = 0

        self.sim['perf'] = {
            'ws_msgs_per_sec': round(self.perf['last_msgs_per_sec'], 2),
            'ws_kb_per_sec': round(self.perf['last_kb_per_sec'], 2),
            'ws_avg_msg_bytes': round(self.perf['last_avg_msg_bytes'], 1),
        }

        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.remove(ws)

    def cancel_task(self) -> None:
        if self.task and not self.task.done():
            # Auto-save progress before cancelling training
            if self.sim['mode'] == 'training':
                 self.save_model(f"{self.sim['map_name']}_model")
            
            # Set mode immediately for UI snappiness
            self.sim['mode'] = 'idle'
            self.task.cancel()
            self.task = None

    async def create_new_map(self) -> str:
        self.env.regenerate_terrain()
        self.agent.reset_memory()
        name = self.map_store.save(self._new_map_name(), self.get_current_map_data())
        self.sim['map_name'] = name
        self.sim['model_name'] = f"{name}_model"
        self.sim['trained_eps'] = 0
        self.sim['episode'] = 0
        self.best_reward = -float('inf')
        await self.sync_state_initial()
        return name

    async def load_map(self, map_name: str) -> bool:
        import os
        map_data = self.map_store.load(map_name)
        if not map_data:
            return False
        self.cancel_task()
        self.env.set_terrain(map_data['target'], map_data['start'], map_data['grid'])
        
        # Auto-load model linked to this map
        model_name = f"{map_name}_model"
        path = self.model_store.path_for(model_name)
        if os.path.exists(path):
            self.agent.load(path)
            self.sim['model_name'] = model_name
            # Set to a conservative value so it starts saving again on improvements
            self.best_reward = -500 
        else:
            self.agent.reset_memory()
            self.sim['model_name'] = model_name
            self.best_reward = -float('inf')

        self.sim['map_name'] = map_name
        self.sim['trained_eps'] = 0
        self.sim['episode'] = 0
        await self.sync_state_initial()
        return True

    def save_model(self, requested_name: str) -> str:
        safe_name = self.model_store.sanitize(requested_name)
        self.sim['model_name'] = safe_name
        path = self.model_store.path_for(safe_name)
        
        # Save in a background thread to prevent blocking the UI
        import threading
        def _save():
            try:
                self.agent.save(path)
                print(f"[+] Model saved to {path}")
            except Exception as e:
                print(f"[!] Save failed: {e}")
        
        threading.Thread(target=_save, daemon=True).start()
        self._refresh_catalogs()
        return safe_name

    async def load_model(self, name: str) -> tuple[bool, str]:
        safe_name = self.model_store.sanitize(name)
        path = self.model_store.path_for(safe_name)
        
        success = self.agent.load(path)
        if not success:
            return False, f"Model '{safe_name}' not found or invalid."

        self.cancel_task()
        self.sim['model_name'] = safe_name
        self.sim['trained_eps'] = 0
        self.sim['episode'] = 0

        # We no longer force the environment to adopt the model's map.
        # It will use whatever the current active map is.
        await self.sync_state_initial()
        return True, ''

    def set_personality(self, name: str) -> bool:
        if name not in QLearningAgent.PERSONALITIES:
            return False
        
        self.cancel_task()
        self.agent = QLearningAgent(
            action_size=self.env.action_space.n,
            personality=name
        )
        self.sim['personality'] = name
        self.sim['epsilon'] = self.agent.epsilon
        self.sim['trained_eps'] = 0
        return True

    def set_speed(self, value: float) -> float:
        self.sim['speed'] = clamp_speed(float(value))
        return self.sim['speed']

    async def start_training(self):
        self.cancel_task()
        self.env.reset() 
        self.sim['rover_pos'] = self.env._agent_location.tolist()
        self.sim['target_pos'] = self.env._target_location.tolist()
        self.sim['mode'] = 'training'
        self.task = asyncio.create_task(self.training_loop())
        await self.broadcast(self.step_payload())

    async def start_run(self):
        self.cancel_task()
        
        # Auto-load the model for the current map if it exists
        map_name = self.sim.get('map_name')
        if map_name:
            import os
            model_name = f"{map_name}_model"
            path = self.model_store.path_for(model_name)
            if os.path.exists(path):
                self.agent.load(path)
                await self.emit_event('info', message=f"Loaded training data for {map_name}")
            else:
                await self.emit_event('info', message=f"No saved data found for {map_name}. Running with current brain.")

        self.env.reset()
        self.sim['rover_pos'] = self.env._agent_location.tolist()
        self.sim['target_pos'] = self.env._target_location.tolist()
        self.sim['mode'] = 'running'
        self.task = asyncio.create_task(self.run_loop())
        await self.broadcast(self.step_payload())

    async def stop_simulation(self):
        self.cancel_task()
        self.env.reset()
        craters, rocks = extract_terrain(self.env.grid)
        self.sim['rover_pos'] = self.env._agent_location.tolist()
        self.sim['target_pos'] = self.env._target_location.tolist()
        self.sim['craters'] = craters
        self.sim['rocks'] = rocks
        self.sim['mode'] = 'idle'
        await self.broadcast(self.step_payload())

    async def pause_simulation(self):
        current_mode = self.sim['mode']
        self.cancel_task()
        if current_mode == 'training':
            self.sim['mode'] = 'paused_training'
        elif current_mode == 'running':
            self.sim['mode'] = 'paused_running'
        await self.broadcast(self.step_payload())

    async def resume_simulation(self):
        current_mode = self.sim['mode']
        self.cancel_task()
        if current_mode == 'paused_training':
            self.sim['mode'] = 'training'
            self.task = asyncio.create_task(self.training_loop(resume=True))
        elif current_mode == 'paused_running':
            self.sim['mode'] = 'running'
            self.task = asyncio.create_task(self.run_loop(resume=True))
        await self.broadcast(self.step_payload())

    async def training_loop(self, resume: bool = False) -> None:
        self.sim['mode'] = 'training'
        if not resume:
            await self.sync_state_initial()
        await self.broadcast(self.static_payload())

        while self.sim['mode'] == 'training':
            if not resume:
                obs, _ = self.env.reset()
                self.sim.update({
                    'target_pos': obs['target'].tolist(),
                    'rover_pos': obs['rover'].tolist(),
                    'step': 0,
                })
            else:
                obs = self.env._get_obs()
                resume = False
            await self.broadcast(self.step_payload())

            done = False
            while not done and self.sim['mode'] == 'training':
                action = self.agent.choose_action(obs)
                next_obs, reward, terminated, truncated, _ = self.env.step(action)
                done = terminated or truncated
                self.agent.learn(obs, action, reward, next_obs, done)
                obs = next_obs

                self.sim['total_reward'] += reward
                self.sim['step'] += 1
                self.sim['rover_pos'] = obs['rover'].tolist()
                self.sim['epsilon'] = round(self.agent.epsilon, 4)

                if terminated and reward > 0:
                    self.sim['last_outcome'] = 'success'
                elif terminated and reward < 0:
                    self.sim['last_outcome'] = 'crater'
                elif truncated:
                    self.sim['last_outcome'] = 'timeout'

                await self.broadcast(self.step_payload())
                await asyncio.sleep(self.sim['speed'])

            self.agent.update_epsilon()
            
            # Update counters
            final_reward = self.sim['total_reward']
            self.sim['episode'] += 1
            self.sim['trained_eps'] += 1
            
            # Broadcast final state with NEW episode number but OLD reward for the chart to catch it
            await self.broadcast(self.step_payload())
            
            # Reset for next episode
            self.sim['total_reward'] = 0.0

            # Auto-save if performance improved
            if final_reward > self.best_reward and self.sim['episode'] > 5:
                self.best_reward = final_reward
                # Link model strictly to map name as requested
                linked_model_name = f"{self.sim['map_name']}_model"
                self.save_model(linked_model_name)
                await self.emit_event('info', message=f"Model updated for {self.sim['map_name']} (Reward: {self.best_reward:.1f})")

            if self.sim['trained_eps'] % 100 == 0:
                linked_model_name = f"{self.sim['map_name']}_model"
                self.save_model(linked_model_name)
                await self.emit_event('saved', trained_eps=self.sim['trained_eps'], models=self.sim.get('models', []), model_name=linked_model_name)

        await self.emit_event('stopped', mode=self.sim['mode'])

    async def run_loop(self, resume: bool = False) -> None:
        self.sim['mode'] = 'running'
        old_eps = self.agent.epsilon
        self.agent.epsilon = 0.0
        self.sim['epsilon'] = 0.0
        if not resume:
            await self.sync_state_initial()
        await self.broadcast(self.static_payload())

        while self.sim['mode'] == 'running':
            if not resume:
                obs, _ = self.env.reset()
                self.sim.update({
                    'target_pos': obs['target'].tolist(),
                    'rover_pos': obs['rover'].tolist(),
                    'step': 0,
                })
            else:
                obs = self.env._get_obs()
                resume = False
            await self.broadcast(self.step_payload())

            done = False
            while not done and self.sim['mode'] == 'running':
                action = self.agent.choose_action(obs)
                next_obs, reward, terminated, truncated, _ = self.env.step(action)
                done = terminated or truncated
                obs = next_obs

                self.sim['total_reward'] += reward
                self.sim['step'] += 1
                self.sim['rover_pos'] = obs['rover'].tolist()

                if terminated and reward > 0:
                    self.sim['last_outcome'] = 'success'
                elif terminated and reward < 0:
                    self.sim['last_outcome'] = 'crater'
                elif truncated:
                    self.sim['last_outcome'] = 'timeout'

                await self.broadcast(self.step_payload())
                await asyncio.sleep(self.sim['speed'])

            self.sim['episode'] += 1
            
            # Broadcast final reward
            await self.broadcast(self.step_payload())
            
            # Reset
            self.sim['total_reward'] = 0.0
            await asyncio.sleep(0.5)

        self.agent.epsilon = old_eps
        await self.emit_event('stopped', mode=self.sim['mode'])

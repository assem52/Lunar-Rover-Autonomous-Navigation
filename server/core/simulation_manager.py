"""
SimulationManager — orchestrates the rover simulation.

Responsibilities:
- Owns the environment, agent, map/model stores, and WebSocket clients.
- Manages simulation state (``self.sim`` dict).
- Handles map/model loading, saving, and personality switching.
- Delegates the actual training and run loops to ``SimRunner``.

What it does NOT do:
- Run step-by-step loops          → see server/core/runner.py
- Define WebSocket message routing → see server/api/ws.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

from fastapi import WebSocket

from ai import QLearningAgent
from envs.lunar_rover import LunarRoverEnv
from server import settings
from server.core.runner import SimRunner
from server.core.stores import MapStore, ModelStore
from server.core.utils import extract_terrain, json_text
from server.core.validation import clamp_speed

log = logging.getLogger(__name__)


class SimulationManager:
    """Top-level coordinator for a single rover simulation session."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Core components
        self.env = LunarRoverEnv(
            size=settings.GRID_SIZE,
            num_craters=settings.NUM_CRATERS,
            num_rocks=settings.NUM_ROCKS,
        )
        self.agent = QLearningAgent(
            action_size=self.env.action_space.n,
            personality=getattr(settings, "DEFAULT_PERSONALITY", "explorer"),
        )
        self.model_store = ModelStore(settings.MODELS_DIR)
        self.map_store   = MapStore(settings.MAPS_DIR)

        # Shared simulation state (read by payloads, written by runner + manager)
        self.sim: dict[str, Any] = {
            "mode":                   "idle",
            "episode":                0,
            "step":                   0,
            "total_reward":           0.0,
            "epsilon":                self.agent.epsilon,
            "rover_pos":              self.env._start_location.tolist(),
            "target_pos":             self.env._target_location.tolist(),
            "craters":                [],
            "rocks":                  [],
            "speed":                  settings.DEFAULT_SPEED,
            "trained_eps":            0,
            "last_outcome":           "",
            "model_name":             settings.DEFAULT_MODEL_NAME,
            "personality":            self.agent.personality_name,
            "available_personalities": list(QLearningAgent.PERSONALITIES.keys()),
            "map_name":               "",
            "reward_history":         [],
            "perf": {
                "ws_msgs_per_sec": 0.0,
                "ws_kb_per_sec":   0.0,
                "ws_avg_msg_bytes": 0.0,
            },
        }

        # WebSocket clients + async task handle
        self.clients: list[WebSocket] = []
        self.task:    asyncio.Task | None = None

        # Training tracker
        self.best_reward: float = -float("inf")

        # Performance counters (for broadcast rate metrics)
        self._perf = {
            "window_start":      time.monotonic(),
            "window_msgs":       0,
            "window_bytes":      0,
            "last_msgs_per_sec": 0.0,
            "last_kb_per_sec":   0.0,
            "last_avg_msg_bytes": 0.0,
        }

        # Loop runner (delegates training / run loops here)
        self._runner = SimRunner(self)

        # Bootstrap: load the first saved map (and its model) if available
        self._bootstrap_map()

    def _bootstrap_map(self) -> None:
        map_names = self.map_store.list_names()
        if map_names:
            first_map = map_names[0]
            map_data  = self.map_store.load(first_map)
            if map_data:
                self.env.set_terrain(map_data["target"], map_data["start"], map_data["grid"])
                self.sim["map_name"] = first_map
                model_name = f"{first_map}_model"
                path = self.model_store.path_for(model_name)
                if os.path.exists(path):
                    self.agent.load(path)
                    self.sim["model_name"] = model_name
                    self.sim["trained_eps"] = getattr(self.agent, "trained_eps", 0)
                    self.sim["episode"] = self.sim["trained_eps"]
                    self.sim["reward_history"] = getattr(self.agent, "reward_history", [])
                    log.info("Auto-loaded model: %s", model_name)
        else:
            # No saved maps yet — persist the freshly generated one
            generated_name = self._new_map_name()
            self.sim["map_name"] = self.map_store.save(
                generated_name, self.get_current_map_data()
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_map_name(self) -> str:
        return f"Map_{len(self.map_store.list_names()) + 1}"

    def get_current_map_data(self) -> dict[str, Any]:
        return {
            "target": self.env._target_location.tolist(),
            "start":  self.env._start_location.tolist(),
            "grid":   self.env.grid.tolist(),
        }

    def _refresh_catalogs(self) -> None:
        self.sim["models"] = self.model_store.list_names()
        self.sim["maps"]   = self.map_store.list_names()
        trained_maps = [
            map_name for map_name in self.sim["maps"]
            if f"{map_name}_model" in self.sim["models"]
        ]
        self.sim["trained_maps"] = trained_maps
        previews: dict[str, dict[str, Any]] = {}
        for map_name in trained_maps:
            map_data = self.map_store.load(map_name)
            if map_data:
                previews[map_name] = map_data
        self.sim["trained_map_previews"] = previews
        trained_models: list[str] = []
        trained_model_previews: dict[str, dict[str, Any]] = {}
        for model_name in self.sim["models"]:
            model_path = self.model_store.path_for(model_name)
            try:
                with open(model_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                map_data = payload.get("map_data")
                if map_data and isinstance(map_data, dict) and "grid" in map_data:
                    trained_models.append(model_name)
                    trained_model_previews[model_name] = map_data
            except Exception:
                continue
        self.sim["trained_models"] = trained_models
        self.sim["trained_model_previews"] = trained_model_previews

    # ------------------------------------------------------------------
    # State sync
    # ------------------------------------------------------------------

    async def sync_state_initial(self) -> None:
        self.env.reset()
        craters, rocks = extract_terrain(self.env.grid)
        self._refresh_catalogs()
        self.sim.update({
            "craters":    craters,
            "rocks":      rocks,
            "target_pos": self.env._target_location.tolist(),
            "rover_pos":  self.env._start_location.tolist(),
        })

    # ------------------------------------------------------------------
    # Payloads
    # ------------------------------------------------------------------

    def static_payload(self) -> dict[str, Any]:
        """Full snapshot — sent on connection and after structural changes."""
        return {
            "mode":                    self.sim["mode"],
            "episode":                 self.sim["episode"],
            "step":                    self.sim["step"],
            "total_reward":            self.sim["total_reward"],
            "epsilon":                 self.sim["epsilon"],
            "rover_pos":               self.sim["rover_pos"],
            "target_pos":              self.sim["target_pos"],
            "craters":                 self.sim["craters"],
            "rocks":                   self.sim["rocks"],
            "trained_eps":             self.sim["trained_eps"],
            "last_outcome":            self.sim["last_outcome"],
            "model_name":              self.sim["model_name"],
            "personality":             self.sim["personality"],
            "available_personalities": self.sim["available_personalities"],
            "reward_history":          self.sim["reward_history"],
            "map_name":                self.sim.get("map_name", ""),
            "models":                  self.sim.get("models", []),
            "maps":                    self.sim.get("maps", []),
            "trained_maps":            self.sim.get("trained_maps", []),
            "trained_map_previews":    self.sim.get("trained_map_previews", {}),
            "trained_models":          self.sim.get("trained_models", []),
            "trained_model_previews":  self.sim.get("trained_model_previews", {}),
            "perf":                    self.sim.get("perf", {}),
        }

    def step_payload(self) -> dict[str, Any]:
        """Lightweight snapshot — sent every simulation step."""
        return {
            "mode":         self.sim["mode"],
            "episode":      self.sim["episode"],
            "step":         self.sim["step"],
            "total_reward": self.sim["total_reward"],
            "epsilon":      self.sim["epsilon"],
            "rover_pos":    self.sim["rover_pos"],
            "target_pos":   self.sim["target_pos"],
            "craters":      self.sim["craters"],
            "rocks":        self.sim["rocks"],
            "trained_eps":  self.sim["trained_eps"],
            "last_outcome": self.sim["last_outcome"],
            "perf":         self.sim.get("perf", {}),
        }

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def emit_event(self, event: str, **data) -> None:
        await self.broadcast({"__event": event, **data})

    async def broadcast(self, data: dict[str, Any]) -> None:
        if not self.clients:
            return

        msg  = json_text(data)
        now  = time.monotonic()
        perf = self._perf

        perf["window_msgs"]  += 1
        perf["window_bytes"] += len(msg.encode("utf-8"))

        elapsed = now - perf["window_start"]
        if elapsed >= 1.0:
            msgs = perf["window_msgs"]
            perf["last_msgs_per_sec"]  = msgs / elapsed
            perf["last_kb_per_sec"]    = (perf["window_bytes"] / 1024.0) / elapsed
            perf["last_avg_msg_bytes"] = perf["window_bytes"] / msgs if msgs else 0.0
            perf["window_start"]  = now
            perf["window_msgs"]   = 0
            perf["window_bytes"]  = 0

        self.sim["perf"] = {
            "ws_msgs_per_sec":  round(perf["last_msgs_per_sec"],  2),
            "ws_kb_per_sec":    round(perf["last_kb_per_sec"],    2),
            "ws_avg_msg_bytes": round(perf["last_avg_msg_bytes"], 1),
        }

        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.remove(ws)

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def cancel_task(self) -> None:
        if self.task and not self.task.done():
            self.sim["mode"] = "idle"
            self.task.cancel()
            self.task = None

    # ------------------------------------------------------------------
    # Map management
    # ------------------------------------------------------------------

    async def create_new_map(self) -> str:
        self.env.regenerate_terrain()
        self.agent.reset_memory()
        name = self.map_store.save(self._new_map_name(), self.get_current_map_data())
        self.sim.update({
            "map_name":   name,
            "model_name": f"{name}_model",
            "trained_eps": 0,
            "episode":    0,
            "reward_history": [],
        })
        self.best_reward = -float("inf")
        await self.sync_state_initial()
        return name

    async def load_map(self, map_name: str) -> bool:
        map_data = self.map_store.load(map_name)
        if not map_data:
            return False
        self.cancel_task()
        self.env.set_terrain(map_data["target"], map_data["start"], map_data["grid"])

        model_name = f"{map_name}_model"
        path = self.model_store.path_for(model_name)
        if os.path.exists(path):
            self.agent.load(path)
            self.best_reward = -500.0  # conservative so new improvements are saved
            self.sim["trained_eps"] = getattr(self.agent, "trained_eps", 0)
            self.sim["episode"] = self.sim["trained_eps"]
            self.sim["reward_history"] = getattr(self.agent, "reward_history", [])
        else:
            self.agent.reset_memory()
            self.best_reward = -float("inf")
            self.sim["trained_eps"] = 0
            self.sim["episode"] = 0
            self.sim["reward_history"] = []

        self.sim.update({
            "map_name":    map_name,
            "model_name":  model_name,
        })
        await self.sync_state_initial()
        return True

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def save_model(self, requested_name: str) -> str:
        safe_name = self.model_store.sanitize(requested_name)
        self.sim["model_name"] = safe_name
        path = self.model_store.path_for(safe_name)

        def _save():
            try:
                map_data = self.get_current_map_data()
                map_data["map_name"] = self.sim.get("map_name", "")
                self.agent.save(path, map_data=map_data, trained_eps=self.sim["trained_eps"], reward_history=self.sim["reward_history"])
                log.info("Model saved → %s", path)
            except Exception as exc:
                log.error("Model save failed: %s", exc)

        threading.Thread(target=_save, daemon=True).start()
        self._refresh_catalogs()
        return safe_name

    async def load_model(self, name: str) -> tuple[bool, str]:
        safe_name = self.model_store.sanitize(name)
        path      = self.model_store.path_for(safe_name)

        if not self.agent.load(path):
            return False, f"Model '{safe_name}' not found or invalid."

        self.cancel_task()
        map_data = getattr(self.agent, "map_data", None)
        if map_data and isinstance(map_data, dict) and {"target", "start", "grid"}.issubset(map_data.keys()):
            self.env.set_terrain(map_data["target"], map_data["start"], map_data["grid"])
            if map_data.get("map_name"):
                self.sim["map_name"] = map_data["map_name"]
        self.sim.update({
            "model_name":  safe_name,
            "trained_eps": getattr(self.agent, "trained_eps", 0),
            "episode":     getattr(self.agent, "trained_eps", 0),
            "reward_history": getattr(self.agent, "reward_history", []),
        })
        await self.sync_state_initial()
        return True, ""

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_personality(self, name: str) -> bool:
        if name not in QLearningAgent.PERSONALITIES:
            return False
        self.cancel_task()
        self.agent = QLearningAgent(action_size=self.env.action_space.n, personality=name)
        self.sim.update({
            "personality":  name,
            "epsilon":      self.agent.epsilon,
            "trained_eps":  0,
            "reward_history": [],
        })
        return True

    def set_speed(self, value: float) -> float:
        self.sim["speed"] = clamp_speed(float(value))
        return self.sim["speed"]

    def set_training_balance(self, exploration: float | None = None, exploitation: float | None = None) -> None:
        if exploration is None and exploitation is None:
            return
        if exploration is None and exploitation is not None:
            exploration = 1.0 - float(exploitation)
        if exploration is None:
            return
        exploration = max(0.01, min(0.99, float(exploration)))
        self.agent.epsilon = exploration
        self.agent.min_epsilon = max(0.01, min(exploration, exploration * 0.15))
        self.sim["epsilon"] = round(self.agent.epsilon, 4)

    # ------------------------------------------------------------------
    # Simulation control (delegate loops to SimRunner)
    # ------------------------------------------------------------------

    async def start_training(self) -> None:
        self.cancel_task()
        self.env.reset()
        self.sim.update({
            "rover_pos":  self.env._agent_location.tolist(),
            "target_pos": self.env._target_location.tolist(),
            "mode":       "training",
        })
        self.task = asyncio.create_task(self._runner.training_loop())
        await self.broadcast(self.step_payload())

    async def train_on_new_map(self, exploration: float | None = None, exploitation: float | None = None) -> str:
        map_name = await self.create_new_map()
        self.set_training_balance(exploration=exploration, exploitation=exploitation)
        await self.start_training()
        return map_name

    async def run_trained_map(self, map_name: str) -> tuple[bool, str]:
        if not map_name:
            return False, "Select a trained map."
        model_name = f"{map_name}_model"
        if model_name not in self.model_store.list_names():
            return False, f"No trained model found for map '{map_name}'."
        ok = await self.load_map(map_name)
        if not ok:
            return False, f"Map '{map_name}' not found."
        self.sim["model_name"] = model_name
        await self.start_run()
        return True, ""

    async def run_trained_model(self, model_name: str) -> tuple[bool, str]:
        if not model_name:
            return False, "Select a trained model."
        ok, err = await self.load_model(model_name)
        if not ok:
            return False, err
        await self.start_run()
        return True, ""

    async def start_run(self) -> None:
        self.cancel_task()

        # Load the selected model first. Fall back to the active-map model.
        selected_model = self.sim.get("model_name", "")
        map_name = self.sim.get("map_name", "")
        map_model_name = f"{map_name}_model" if map_name else ""

        candidate_names = [n for n in (selected_model, map_model_name) if n]
        loaded_name = ""
        for candidate in candidate_names:
            path = self.model_store.path_for(candidate)
            if os.path.exists(path) and self.agent.load(path):
                loaded_name = candidate
                self.sim["model_name"] = candidate
                break

        if loaded_name:
            await self.emit_event("info", message=f"Loaded model: {loaded_name}")
        else:
            await self.emit_event("info", message="No saved model found. Running with current brain.")

        self.env.reset()
        self.sim.update({
            "rover_pos":  self.env._agent_location.tolist(),
            "target_pos": self.env._target_location.tolist(),
            "mode":       "running",
        })
        self.task = asyncio.create_task(self._runner.run_loop())
        await self.broadcast(self.step_payload())

    async def stop_simulation(self) -> None:
        self.cancel_task()
        self.env.reset()
        craters, rocks = extract_terrain(self.env.grid)
        self.sim.update({
            "rover_pos":  self.env._agent_location.tolist(),
            "target_pos": self.env._target_location.tolist(),
            "craters":    craters,
            "rocks":      rocks,
            "mode":       "idle",
        })
        await self.broadcast(self.step_payload())

    async def stop_and_save(self, model_name: str) -> str:
        saved_name = self.save_model(model_name)
        await self.stop_simulation()
        return saved_name

    async def pause_simulation(self) -> None:
        current_mode = self.sim["mode"]
        self.cancel_task()
        if current_mode == "training":
            self.sim["mode"] = "paused_training"
        elif current_mode == "running":
            self.sim["mode"] = "paused_running"
        await self.broadcast(self.step_payload())

    async def resume_simulation(self) -> None:
        current_mode = self.sim["mode"]
        self.cancel_task()
        if current_mode == "paused_training":
            self.sim["mode"] = "training"
            self.task = asyncio.create_task(self._runner.training_loop(resume=True))
        elif current_mode == "paused_running":
            self.sim["mode"] = "running"
            self.task = asyncio.create_task(self._runner.run_loop(resume=True))
        await self.broadcast(self.step_payload())

"""
SimRunner — isolated training and run loops.

Responsible for:
- Executing one episode step-by-step (training / inference).
- Applying outcome labels (success / crater / timeout).

SimRunner is intentionally stateless beyond what it receives from
SimulationManager; it writes results back through the shared ``sim``
dict and the ``broadcast`` / ``emit_event`` callables so the manager
stays in charge of the WebSocket layer.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Coroutine

if TYPE_CHECKING:
    from server.core.simulation_manager import SimulationManager


class SimRunner:
    """Runs training and inference loops on behalf of SimulationManager."""

    def __init__(self, manager: "SimulationManager") -> None:
        self._m = manager  # back-reference to the owning manager

    # ------------------------------------------------------------------
    # Internal helpers (delegate everything to the manager)
    # ------------------------------------------------------------------

    @property
    def _sim(self) -> dict[str, Any]:
        return self._m.sim

    async def _broadcast_step(self) -> None:
        await self._m.broadcast(self._m.step_payload())

    async def _broadcast_full(self) -> None:
        await self._m.broadcast(self._m.static_payload())

    async def _emit(self, event: str, **kw) -> None:
        await self._m.emit_event(event, **kw)

    def _sleep(self) -> Coroutine:
        return asyncio.sleep(self._sim["speed"])

    @staticmethod
    def _outcome(terminated: bool, truncated: bool, reward: float) -> str:
        if terminated and reward > 0:
            return "success"
        if terminated:
            return "crater"
        if truncated:
            return "timeout"
        return ""

    # ------------------------------------------------------------------
    # Training loop
    # ------------------------------------------------------------------

    async def training_loop(self, resume: bool = False) -> None:
        m = self._m
        sim = self._sim

        sim["mode"] = "training"
        if not resume:
            await m.sync_state_initial()
        await self._broadcast_full()

        while sim["mode"] == "training":
            # ── Episode start ──────────────────────────────────────────
            if not resume:
                obs, _ = m.env.reset()
                sim.update({
                    "target_pos": obs["target"].tolist(),
                    "rover_pos":  obs["rover"].tolist(),
                    "step": 0,
                })
            else:
                obs = m.env._get_obs()
                resume = False
            await self._broadcast_step()
            await self._sleep()

            # ── Step loop ──────────────────────────────────────────────
            done = False
            while not done and sim["mode"] == "training":
                action = m.agent.choose_action(obs)
                next_obs, reward, terminated, truncated, _ = m.env.step(action)
                done = terminated or truncated
                m.agent.learn(obs, action, reward, next_obs, done)
                obs = next_obs

                sim["total_reward"] += reward
                sim["step"]         += 1
                sim["rover_pos"]     = obs["rover"].tolist()
                sim["epsilon"]       = round(m.agent.epsilon, 4)

                outcome = self._outcome(terminated, truncated, reward)
                if outcome:
                    sim["last_outcome"] = outcome

                await self._broadcast_step()
                await self._sleep()

            # ── Episode end ────────────────────────────────────────────
            m.agent.update_epsilon()

            final_reward     = sim["total_reward"]
            sim["episode"]   += 1
            sim["trained_eps"] += 1
            
            # Save history for chart
            sim["reward_history"].append(final_reward)
            if len(sim["reward_history"]) > 1000:
                sim["reward_history"] = sim["reward_history"][-1000:]

            # Broadcast with updated episode counter so the chart captures it
            await self._broadcast_step()

            sim["total_reward"] = 0.0

        await self._emit("stopped", mode=sim["mode"])

    # ------------------------------------------------------------------
    # Run (inference) loop
    # ------------------------------------------------------------------

    async def run_loop(self, resume: bool = False) -> None:
        m = self._m
        sim = self._sim

        sim["mode"]    = "running"
        old_eps        = m.agent.epsilon
        m.agent.epsilon = 0.0
        sim["epsilon"] = 0.0

        if not resume:
            await m.sync_state_initial()
        await self._broadcast_full()

        while sim["mode"] == "running":
            # ── Episode start ──────────────────────────────────────────
            if not resume:
                obs, _ = m.env.reset()
                sim.update({
                    "target_pos": obs["target"].tolist(),
                    "rover_pos":  obs["rover"].tolist(),
                    "step": 0,
                })
            else:
                obs = m.env._get_obs()
                resume = False
            await self._broadcast_step()
            await self._sleep()

            # ── Step loop ──────────────────────────────────────────────
            done = False
            while not done and sim["mode"] == "running":
                action = m.agent.choose_action(obs)
                next_obs, reward, terminated, truncated, _ = m.env.step(action)
                done = terminated or truncated
                obs  = next_obs

                sim["total_reward"] += reward
                sim["step"]         += 1
                sim["rover_pos"]     = obs["rover"].tolist()

                outcome = self._outcome(terminated, truncated, reward)
                if outcome:
                    sim["last_outcome"] = outcome

                await self._broadcast_step()
                await self._sleep()

            # ── Episode end ────────────────────────────────────────────
            sim["episode"] += 1
            await self._broadcast_step()
            sim["total_reward"] = 0.0
            await asyncio.sleep(0.5)

        m.agent.epsilon = old_eps
        await self._emit("stopped", mode=sim["mode"])

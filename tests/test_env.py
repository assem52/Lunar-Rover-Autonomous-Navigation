"""
Unit tests for the LunarRoverEnv.

Run with:  python -m pytest tests/ -v
"""
import numpy as np
import pytest

from envs.lunar_rover import (
    INITIAL_ENERGY,
    REWARD_CRATER,
    REWARD_OUT_BOUNDS,
    REWARD_ROCK_HIT,
    REWARD_STEP,
    REWARD_TARGET,
    REWARD_TIMEOUT,
    LunarRoverEnv,
    TerrainType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_env(size: int = 5) -> LunarRoverEnv:
    """Small deterministic environment for fast tests."""
    return LunarRoverEnv(size=size, num_craters=0, num_rocks=0)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_reset_returns_correct_keys(self):
        env = make_env()
        obs, info = env.reset()
        assert set(obs.keys()) == {"rover", "target", "grid"}

    def test_grid_shape(self):
        env = make_env(size=7)
        obs, _ = env.reset()
        assert obs["grid"].shape == (7, 7)

    def test_rover_starts_bottom_left(self):
        env = make_env()
        obs, _ = env.reset()
        assert obs["rover"][0] == 0
        assert obs["rover"][1] == env.size - 1

    def test_energy_reset(self):
        env = make_env()
        env.reset()
        assert env.energy == float(INITIAL_ENERGY)


# ---------------------------------------------------------------------------
# Movement & Bounds
# ---------------------------------------------------------------------------

class TestMovement:
    def test_step_moves_rover_right(self):
        env = make_env()
        env.reset()
        start_x = env._agent_location[0]
        # Action 0 = right
        obs, reward, terminated, truncated, _ = env.step(0)
        assert obs["rover"][0] == start_x + 1

    def test_step_penalty_applied(self):
        env = make_env()
        env.reset()
        _, reward, terminated, truncated, _ = env.step(0)
        # Normal move on empty terrain: just the step penalty
        assert reward == REWARD_STEP
        assert not terminated
        assert not truncated

    def test_out_of_bounds_left(self):
        env = make_env()
        env.reset()
        # Rover is at x=0; moving left (action 2) goes out of bounds
        obs, reward, terminated, truncated, _ = env.step(2)
        assert reward == REWARD_OUT_BOUNDS
        assert not terminated
        assert obs["rover"][0] == 0  # position unchanged

    def test_out_of_bounds_up(self):
        """Rover at bottom row, trying to move up past the top edge."""
        env = make_env(size=3)
        env.reset()
        # Move up twice to reach row 0, then once more
        env.step(1)  # up
        env.step(1)  # up → now at y=1 from top (0-indexed)
        # At (0, 0) now; try moving up again
        obs, reward, terminated, truncated, _ = env.step(1)
        assert reward == REWARD_OUT_BOUNDS


# ---------------------------------------------------------------------------
# Terrain interactions
# ---------------------------------------------------------------------------

class TestTerrain:
    def _env_with_crater_at(self, x, y, size=5):
        env = make_env(size=size)
        env.reset()
        env.grid[y, x] = TerrainType.CRATER.value
        return env

    def _env_with_rock_at(self, x, y, size=5):
        env = make_env(size=size)
        env.reset()
        env.grid[y, x] = TerrainType.ROCK.value
        return env

    def test_crater_terminates_episode(self):
        # Rover at (0,4); place crater at (1,4)
        env = self._env_with_crater_at(x=1, y=4)
        _, reward, terminated, truncated, _ = env.step(0)  # move right into crater
        assert reward == REWARD_CRATER
        assert terminated

    def test_rock_blocks_movement(self):
        # Rover at (0,4); place rock at (1,4)
        env = self._env_with_rock_at(x=1, y=4)
        obs, reward, terminated, truncated, _ = env.step(0)
        # rover should NOT have moved
        assert obs["rover"][0] == 0
        assert reward == REWARD_STEP + REWARD_ROCK_HIT
        assert not terminated

    def test_reach_target_gives_positive_reward(self):
        env = make_env(size=3)
        env.reset()
        # Force target directly to the right of the rover
        env._target_location = np.array([1, env.size - 1], dtype=int)
        _, reward, terminated, truncated, _ = env.step(0)  # move right
        assert reward == REWARD_TARGET
        assert terminated


# ---------------------------------------------------------------------------
# Energy / Truncation
# ---------------------------------------------------------------------------

class TestEnergy:
    def test_energy_decrements_each_step(self):
        env = make_env()
        env.reset()
        env.step(0)
        assert env.energy == float(INITIAL_ENERGY) - 1

    def test_truncation_when_energy_zero(self):
        env = make_env(size=20)
        env.reset()
        env.energy = 1.0  # force energy to expire on next step
        _, reward, terminated, truncated, _ = env.step(0)
        assert truncated
        assert reward <= REWARD_STEP + REWARD_TIMEOUT  # timeout penalty applied

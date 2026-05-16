import gymnasium as gym
from gymnasium import spaces
import numpy as np
from enum import Enum


class Actions(Enum):
    right = 0
    up = 1
    left = 2
    down = 3


class TerrainType(Enum):
    NORMAL = 0
    CRATER = 1
    ROCK = 2
    TARGET = 3


class LunarRoverEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, render_mode=None, size=15, num_craters=5, num_rocks=10):
        super().__init__()
        self.size = size
        self.window_size = 512
        self.num_craters = num_craters
        self.num_rocks = num_rocks

        # Observations: rover pos, target pos, and grid mapping
        # Grid: 0=normal, 1=crater, 2=rock
        self.observation_space = spaces.Dict(
            {
                "rover": spaces.Box(0, size - 1, shape=(2,), dtype=int),
                "target": spaces.Box(0, size - 1, shape=(2,), dtype=int),
                "grid": spaces.Box(0, 2, shape=(size, size), dtype=int),
            }
        )

        self.action_space = spaces.Discrete(4)

        self._action_to_direction = {
            Actions.right.value: np.array([1, 0]),
            Actions.up.value: np.array([0, -1]), # In Pygame, y goes down
            Actions.left.value: np.array([-1, 0]),
            Actions.down.value: np.array([0, 1]),
        }

        self.render_mode = render_mode
        
        # Generate terrain once to make it static
        self._generate_terrain()
        # Save the starting location so we can reset to it
        self._start_location = self._agent_location.copy()

    def regenerate_terrain(self):
        """Force generation of a new random map"""
        self._generate_terrain()
        self._start_location = self._agent_location.copy()
        
    def set_terrain(self, target_pos, start_pos, grid):
        """Set a specific map (used when loading a saved model)"""
        self._target_location = np.array(target_pos)
        # Force start to bottom-left even for loaded maps
        self._agent_location = np.array([0, self.size - 1], dtype=int)
        self._start_location = self._agent_location.copy()
        self.grid = np.array(grid)

    def _generate_terrain(self):
        self.grid = np.zeros((self.size, self.size), dtype=int)
        
        def random_pos():
            return self.np_random.integers(0, self.size, size=2, dtype=int)

        # Place target
        self._target_location = random_pos()

        # Place rover (Fixed at bottom-left corner)
        self._agent_location = np.array([0, self.size - 1], dtype=int)
        while np.array_equal(self._agent_location, self._target_location):
            self._target_location = random_pos()

        # Place craters
        craters_placed = 0
        while craters_placed < self.num_craters:
            pos = random_pos()
            if not np.array_equal(pos, self._target_location) and not np.array_equal(pos, self._agent_location) and self.grid[pos[1], pos[0]] == TerrainType.NORMAL.value:
                self.grid[pos[1], pos[0]] = TerrainType.CRATER.value
                craters_placed += 1

        # Place rocks
        rocks_placed = 0
        while rocks_placed < self.num_rocks:
            pos = random_pos()
            if not np.array_equal(pos, self._target_location) and not np.array_equal(pos, self._agent_location) and self.grid[pos[1], pos[0]] == TerrainType.NORMAL.value:
                self.grid[pos[1], pos[0]] = TerrainType.ROCK.value
                rocks_placed += 1

    def _get_obs(self):
        return {
            "rover": self._agent_location,
            "target": self._target_location,
            "grid": self.grid
        }

    def _get_info(self):
        return {
            "distance": np.linalg.norm(self._agent_location - self._target_location, ord=1)
        }

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Reset rover to its original starting location
        self._agent_location = self._start_location.copy()
        
        self.energy = 100.0



        return self._get_obs(), self._get_info()

    def step(self, action):
        direction = self._action_to_direction[action]
        new_location = self._agent_location + direction
        
        # Check bounds
        if not (0 <= new_location[0] < self.size and 0 <= new_location[1] < self.size):
            # Out of bounds: penalty, don't move
            return self._get_obs(), -5, False, False, self._get_info()

        terrain_at_new = self.grid[new_location[1], new_location[0]]

        reward = -1 # Small penalty for each step to encourage fast arrival
        terminated = False
        
        if terrain_at_new == TerrainType.ROCK.value:
            # Hit a rock, don't move, penalty
            reward -= 5
        else:
            # Move
            self._agent_location = new_location
            
            if terrain_at_new == TerrainType.CRATER.value:
                # Fell in crater, terminal state
                reward = -100
                terminated = True
            elif np.array_equal(self._agent_location, self._target_location):
                # Reached target!
                reward = 100
                terminated = True

        self.energy -= 1 # Consume energy
        truncated = self.energy <= 0
        if truncated:
             reward -= 50



        return self._get_obs(), reward, terminated, truncated, self._get_info()

    def render(self):
        pass

    def close(self):
        pass

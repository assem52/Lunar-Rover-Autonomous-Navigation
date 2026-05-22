import random

import numpy as np

from ai.core.config import QLearningConfig
from ai.core.persistence import build_q_table, load_q_table, save_q_table
from ai.core.state_encoder import encode_lunar_state
from envs.lunar_rover import REWARD_CRATER, REWARD_ROCK_HIT, REWARD_STEP


class QLearningAgent:
    # Maps personality name → QLearningConfig factory method name
    PERSONALITIES: dict[str, str] = {
        "explorer": "explorer",
        "cautious":  "cautious",
        "sprinter":  "sprinter",
        "clumsy":    "clumsy",
    }

    def __init__(self, action_size: int, personality: str = "explorer"):
        self.action_size = action_size
        self.personality_name = personality if personality in self.PERSONALITIES else "explorer"

        # Build config from the named preset
        preset_name = self.PERSONALITIES[self.personality_name]
        cfg: QLearningConfig = getattr(QLearningConfig, preset_name)()
        self._cfg = cfg

        # Expose flat attributes so the rest of the code stays unchanged
        self.lr            = cfg.learning_rate
        self.gamma         = cfg.discount_factor
        self.epsilon       = cfg.epsilon
        self.epsilon_decay = cfg.epsilon_decay
        self.min_epsilon   = cfg.min_epsilon

        self.multipliers = {
            "rock":   cfg.rock_mult,
            "crater": cfg.crater_mult,
            "step":   cfg.step_mult,
        }

        self.q_table = build_q_table(action_size)

    def _state_key(self, state):
        return encode_lunar_state(state)

    def choose_action(self, state):
        key = self._state_key(state)
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        return int(np.argmax(self.q_table[key]))

    def learn(self, state, action, reward, next_state, done):
        # Scale reward subjectively based on personality
        shaped_reward = reward
        if reward == REWARD_STEP:          # plain step cost
            shaped_reward *= self.multipliers["step"]
        elif reward <= REWARD_CRATER:      # fell into crater (terminal)
            shaped_reward *= self.multipliers["crater"]
        elif reward <= REWARD_ROCK_HIT:    # hit a rock / out of bounds
            shaped_reward *= self.multipliers["rock"]

        state_key      = self._state_key(state)
        next_state_key = self._state_key(next_state)

        target = shaped_reward
        if not done:
            target += self.gamma * np.max(self.q_table[next_state_key])

        self.q_table[state_key][action] += self.lr * (target - self.q_table[state_key][action])

    def update_epsilon(self):
        if self.epsilon > self.min_epsilon:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.min_epsilon, self.epsilon)

    def save(self, filepath: str, map_data=None, trained_eps: int = 0, reward_history: list = None) -> None:
        save_q_table(filepath, self.q_table, self.epsilon, map_data, trained_eps, reward_history)

    def load(self, filepath: str) -> bool:
        try:
            q_table, epsilon, map_data, trained_eps, reward_history = load_q_table(filepath, self.action_size)
            self.q_table = q_table
            if epsilon is not None:
                self.epsilon = epsilon
            self.trained_eps = trained_eps
            self.reward_history = reward_history
            self.map_data = map_data
            return True
        except:
            return False

    def reset_memory(self):
        self.q_table = build_q_table(self.action_size)
        self.epsilon = self._cfg.epsilon  # reset to the preset's initial epsilon

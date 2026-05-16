import random

import numpy as np

from ai.core.config import QLearningConfig
from ai.core.persistence import build_q_table, load_q_table, save_q_table
from ai.core.state_encoder import encode_lunar_state


class QLearningAgent:
    PERSONALITIES = {
        "explorer": {
            "lr": 0.1, "gamma": 0.99, "epsilon": 0.4, "decay": 0.999, "min_eps": 0.05,
            "rock_mult": 1.0, "crater_mult": 1.0, "step_mult": 0.5
        },
        "cautious": {
            "lr": 0.05, "gamma": 0.8, "epsilon": 0.1, "decay": 0.99, "min_eps": 0.01,
            "rock_mult": 5.0, "crater_mult": 10.0, "step_mult": 1.0
        },
        "sprinter": {
            "lr": 0.2, "gamma": 0.9, "epsilon": 0.2, "decay": 0.995, "min_eps": 0.02,
            "rock_mult": 1.0, "crater_mult": 2.0, "step_mult": 5.0
        },
        "clumsy": {
            "lr": 0.1, "gamma": 0.5, "epsilon": 0.8, "decay": 1.0, "min_eps": 0.5,
            "rock_mult": 1.0, "crater_mult": 1.0, "step_mult": 1.0
        }
    }

    def __init__(self, action_size: int, personality: str = "explorer"):
        self.action_size = action_size
        self.personality_name = personality if personality in self.PERSONALITIES else "explorer"
        p = self.PERSONALITIES[self.personality_name]
        
        self.lr = p["lr"]
        self.gamma = p["gamma"]
        self.epsilon = p["epsilon"]
        self.epsilon_decay = p["decay"]
        self.min_epsilon = p["min_eps"]
        
        self.multipliers = {
            "rock": p["rock_mult"],
            "crater": p["crater_mult"],
            "step": p["step_mult"]
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
        # Subjective reward scaling based on personality
        shaped_reward = reward
        if reward == -1: # Step
            shaped_reward *= self.multipliers["step"]
        elif reward <= -100: # Crater
            shaped_reward *= self.multipliers["crater"]
        elif reward <= -5: # Rock or Out of bounds
            shaped_reward *= self.multipliers["rock"]

        state_key = self._state_key(state)
        next_state_key = self._state_key(next_state)

        target = shaped_reward
        if not done:
            target += self.gamma * np.max(self.q_table[next_state_key])

        self.q_table[state_key][action] += self.lr * (target - self.q_table[state_key][action])

    def update_epsilon(self):
        if self.epsilon > self.min_epsilon:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.min_epsilon, self.epsilon)

    def save(self, filepath, map_data=None):
        save_q_table(filepath, self.q_table, self.epsilon, map_data)

    def load(self, filepath):
        q_table, epsilon, _ = load_q_table(filepath, self.action_size)
        if epsilon is None:
            return False
        self.q_table = q_table
        self.epsilon = epsilon
        return True

    def reset_memory(self):
        self.q_table = build_q_table(self.action_size)
        p = self.PERSONALITIES[self.personality_name]
        self.epsilon = p["epsilon"]

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class QLearningConfig:
    """Hyperparameters for a single Q-Learning agent."""

    # Core learning parameters
    learning_rate:   float = 0.1
    discount_factor: float = 0.99
    epsilon:         float = 1.0
    epsilon_decay:   float = 0.995
    min_epsilon:     float = 0.01

    # Per-event reward multipliers (subjective reward shaping)
    rock_mult:   float = 1.0
    crater_mult: float = 1.0
    step_mult:   float = 1.0

    # ---------------------------------------------------------------------------
    # Named presets — these replace the raw PERSONALITIES dict in the agent
    # ---------------------------------------------------------------------------
    @classmethod
    def explorer(cls) -> QLearningConfig:
        """Explores freely; learns slowly but thoroughly."""
        return cls(learning_rate=0.1, discount_factor=0.99,
                   epsilon=0.4, epsilon_decay=0.999, min_epsilon=0.05,
                   rock_mult=1.0, crater_mult=1.0, step_mult=0.5)

    @classmethod
    def cautious(cls) -> QLearningConfig:
        """Strongly avoids craters; converges quickly but may be suboptimal."""
        return cls(learning_rate=0.05, discount_factor=0.8,
                   epsilon=0.1, epsilon_decay=0.99, min_epsilon=0.01,
                   rock_mult=5.0, crater_mult=10.0, step_mult=1.0)

    @classmethod
    def sprinter(cls) -> QLearningConfig:
        """Optimises for speed; accepts higher crash risk."""
        return cls(learning_rate=0.2, discount_factor=0.9,
                   epsilon=0.2, epsilon_decay=0.995, min_epsilon=0.02,
                   rock_mult=1.0, crater_mult=2.0, step_mult=5.0)

    @classmethod
    def clumsy(cls) -> QLearningConfig:
        """Intentionally bad baseline: high, non-decaying epsilon."""
        return cls(learning_rate=0.1, discount_factor=0.5,
                   epsilon=0.8, epsilon_decay=1.0, min_epsilon=0.5,
                   rock_mult=1.0, crater_mult=1.0, step_mult=1.0)

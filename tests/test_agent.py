"""
Unit tests for QLearningAgent.

Run with:  python -m pytest tests/ -v
"""
import numpy as np
import pytest

from ai.agents.q_learning_agent import QLearningAgent
from ai.core.config import QLearningConfig
from envs.lunar_rover import LunarRoverEnv, REWARD_TARGET, REWARD_CRATER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(personality: str = "explorer") -> QLearningAgent:
    return QLearningAgent(action_size=4, personality=personality)


def dummy_state(rover=(0, 9), target=(5, 0), size=10):
    env = LunarRoverEnv(size=size, num_craters=0, num_rocks=0)
    env.reset()
    env._agent_location = np.array(rover, dtype=int)
    env._target_location = np.array(target, dtype=int)
    return env._get_obs()


# ---------------------------------------------------------------------------
# Construction & Personalities
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_all_personalities_create_without_error(self):
        for name in QLearningAgent.PERSONALITIES:
            agent = QLearningAgent(action_size=4, personality=name)
            assert agent.personality_name == name

    def test_unknown_personality_falls_back_to_explorer(self):
        agent = QLearningAgent(action_size=4, personality="nonexistent")
        assert agent.personality_name == "explorer"

    def test_config_wired_correctly_for_cautious(self):
        agent = make_agent("cautious")
        cfg = QLearningConfig.cautious()
        assert agent.lr == cfg.learning_rate
        assert agent.gamma == cfg.discount_factor
        assert agent.epsilon == cfg.epsilon
        assert agent.multipliers["crater"] == cfg.crater_mult

    def test_clumsy_epsilon_does_not_decay(self):
        agent = make_agent("clumsy")
        original = agent.epsilon
        for _ in range(100):
            agent.update_epsilon()
        assert agent.epsilon == pytest.approx(original)

    def test_explorer_epsilon_decays(self):
        agent = make_agent("explorer")
        original = agent.epsilon
        for _ in range(50):
            agent.update_epsilon()
        assert agent.epsilon < original


# ---------------------------------------------------------------------------
# Action selection
# ---------------------------------------------------------------------------

class TestActionSelection:
    def test_returns_valid_action(self):
        agent = make_agent()
        state = dummy_state()
        action = agent.choose_action(state)
        assert 0 <= action < 4

    def test_greedy_when_epsilon_zero(self):
        """With epsilon=0 the agent always exploits the q-table."""
        agent = make_agent()
        agent.epsilon = 0.0
        state = dummy_state()
        # Force a known best action in the q-table
        key = agent._state_key(state)
        agent.q_table[key][:] = [0.0, 0.0, 99.0, 0.0]  # action 2 is best
        action = agent.choose_action(state)
        assert action == 2

    def test_random_when_epsilon_one(self):
        """With epsilon=1 actions should vary (probabilistic test)."""
        agent = make_agent()
        agent.epsilon = 1.0
        state = dummy_state()
        actions = {agent.choose_action(state) for _ in range(50)}
        assert len(actions) > 1  # must have explored more than one action


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------

class TestLearning:
    def test_q_value_increases_after_positive_reward(self):
        agent = make_agent()
        agent.epsilon = 0.0
        state = dummy_state()
        next_state = dummy_state(rover=(1, 9))
        key = agent._state_key(state)

        before = agent.q_table[key][0]
        agent.learn(state, action=0, reward=REWARD_TARGET, next_state=next_state, done=True)
        after = agent.q_table[key][0]

        assert after > before

    def test_q_value_decreases_after_crater(self):
        agent = make_agent()
        state = dummy_state()
        next_state = dummy_state(rover=(1, 9))
        key = agent._state_key(state)

        before = agent.q_table[key][0]
        agent.learn(state, action=0, reward=REWARD_CRATER, next_state=next_state, done=True)
        after = agent.q_table[key][0]

        assert after < before

    def test_personality_multiplier_applied(self):
        """Cautious should amplify crater penalty more than explorer."""
        state = dummy_state()
        next_state = dummy_state(rover=(1, 9))

        agent_explorer = make_agent("explorer")
        agent_cautious = make_agent("cautious")

        key_e = agent_explorer._state_key(state)
        key_c = agent_cautious._state_key(state)

        agent_explorer.learn(state, 0, REWARD_CRATER, next_state, True)
        agent_cautious.learn(state, 0, REWARD_CRATER, next_state, True)

        # Cautious multiplier is 10x vs explorer 1x, so cautious Q should be lower
        assert agent_cautious.q_table[key_c][0] < agent_explorer.q_table[key_e][0]


# ---------------------------------------------------------------------------
# Memory reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_memory_clears_q_table(self):
        agent = make_agent()
        state = dummy_state()
        next_state = dummy_state(rover=(1, 9))
        # train a bit so q-table is non-empty
        for _ in range(10):
            agent.learn(state, 0, REWARD_TARGET, next_state, True)

        agent.reset_memory()
        key = agent._state_key(state)
        assert np.all(agent.q_table[key] == 0.0)

    def test_reset_memory_restores_initial_epsilon(self):
        agent = make_agent("explorer")
        initial_eps = agent.epsilon
        # decay it artificially
        agent.epsilon = 0.001
        agent.reset_memory()
        assert agent.epsilon == pytest.approx(initial_eps)

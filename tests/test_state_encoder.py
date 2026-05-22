"""
Unit tests for the state encoder.

Run with:  python -m pytest tests/ -v
"""
import numpy as np
import pytest

from ai.core.state_encoder import encode_lunar_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(rover, target, size=10, grid=None):
    g = np.zeros((size, size), dtype=int) if grid is None else np.array(grid)
    return {"rover": np.array(rover), "target": np.array(target), "grid": g}


# ---------------------------------------------------------------------------
# State key structure
# ---------------------------------------------------------------------------

class TestEncoding:
    def test_returns_string(self):
        state = make_state(rover=(0, 9), target=(5, 0))
        key = encode_lunar_state(state)
        assert isinstance(key, str)

    def test_key_contains_target_prefix(self):
        state = make_state(rover=(0, 9), target=(5, 0))
        key = encode_lunar_state(state)
        assert key.startswith("t:")

    def test_key_contains_vision_section(self):
        state = make_state(rover=(5, 5), target=(0, 0))
        key = encode_lunar_state(state)
        assert "|v:" in key

    def test_different_positions_give_different_keys(self):
        s1 = make_state(rover=(0, 9), target=(5, 0))
        s2 = make_state(rover=(1, 9), target=(5, 0))
        assert encode_lunar_state(s1) != encode_lunar_state(s2)

    def test_same_relative_direction_same_key(self):
        """Two states with identical local view and target direction → same key."""
        grid = np.zeros((10, 10), dtype=int)
        s1 = make_state(rover=(3, 7), target=(5, 5), grid=grid)
        s2 = make_state(rover=(3, 7), target=(5, 5), grid=grid)
        assert encode_lunar_state(s1) == encode_lunar_state(s2)

    def test_obstacle_in_local_view_changes_key(self):
        """Placing a rock next to the rover should produce a different key."""
        grid_clear = np.zeros((10, 10), dtype=int)
        grid_rock  = np.zeros((10, 10), dtype=int)
        grid_rock[8, 1] = 2  # rock at (1, 8), right of rover at (0, 9)

        s_clear = make_state(rover=(0, 9), target=(5, 0), grid=grid_clear)
        s_rock  = make_state(rover=(0, 9), target=(5, 0), grid=grid_rock)

        assert encode_lunar_state(s_clear) != encode_lunar_state(s_rock)

    def test_out_of_bounds_cells_treated_as_rock(self):
        """Rover at the corner — OOB cells must appear as '2' (rock) in the vision."""
        state = make_state(rover=(0, 0), target=(5, 5))
        key = encode_lunar_state(state)
        # The vision segment comes after "|v:"
        vision = key.split("|v:")[1]
        # There are 8 surrounding cells; OOB ones should be '2'
        assert "2" in vision

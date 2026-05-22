import json
from typing import Any


def extract_terrain(grid):
    craters, rocks = [], []
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if grid[i, j] == 1:
                craters.append([j, i])
            elif grid[i, j] == 2:
                rocks.append([j, i])
    return craters, rocks


def json_text(data: dict[str, Any]) -> str:
    return json.dumps(data)

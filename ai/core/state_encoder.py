def encode_lunar_state(state: dict) -> str:
    rover = state['rover']
    target = state['target']
    grid = state['grid']
    size = grid.shape[0]

    # 1. Relative target direction (3x3 = 9 directions)
    dx = target[0] - rover[0]
    dy = target[1] - rover[1]
    rel_dir = f"{1 if dx > 0 else -1 if dx < 0 else 0},{1 if dy > 0 else -1 if dy < 0 else 0}"
    
    # 2. Local vision (3x3 grid around the rover)
    local_view = []
    for oy in range(-1, 2):
        for ox in range(-1, 2):
            if oy == 0 and ox == 0: continue
            nx, ny = rover[0] + ox, rover[1] + oy
            if 0 <= nx < size and 0 <= ny < size:
                local_view.append(str(int(grid[ny, nx])))
            else:
                local_view.append('2') # Treat out of bounds as rock (impassable)
    
    vision = "".join(local_view)
    return f"t:{rel_dir}|v:{vision}"

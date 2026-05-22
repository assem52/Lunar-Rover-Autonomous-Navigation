import glob
import json
import os
import re
from datetime import datetime
from typing import Any

from server.core.naming import sanitize_name


class MapStore:
    def __init__(self, maps_dir: str):
        self.maps_dir = maps_dir

    def list_names(self) -> list[str]:
        files = glob.glob(os.path.join(self.maps_dir, '*.json'))
        names = [os.path.splitext(os.path.basename(f))[0] for f in files]
        return sorted(names, key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])

    def path_for(self, name: str) -> str:
        safe = sanitize_name(name, 'map')
        return os.path.join(self.maps_dir, f'{safe}.json')

    def save(self, name: str, map_data: dict[str, Any]) -> str:
        safe = sanitize_name(name, 'map')
        path = self.path_for(safe)
        payload = {
            'name': safe,
            'saved_at': datetime.utcnow().isoformat() + 'Z',
            'map_data': map_data,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        return safe

    def load(self, name: str) -> dict[str, Any] | None:
        path = self.path_for(name)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('map_data')


class ModelStore:
    def __init__(self, models_dir: str):
        self.models_dir = models_dir

    def list_names(self) -> list[str]:
        files = glob.glob(os.path.join(self.models_dir, '*.json'))
        names = [os.path.splitext(os.path.basename(f))[0] for f in files]
        return sorted(names, key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])

    def path_for(self, name: str) -> str:
        safe = sanitize_name(name, 'model')
        return os.path.join(self.models_dir, f'{safe}.json')

    def sanitize(self, name: str) -> str:
        return sanitize_name(name, 'model')

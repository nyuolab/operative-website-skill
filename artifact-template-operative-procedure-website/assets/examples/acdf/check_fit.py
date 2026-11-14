"""Check the cervical example's neural clearances, seated implants and tool trajectories."""

import argparse
from itertools import product
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from mesh_geometry import contains, decode_triangles, triangle_crossings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mesh_data', type=Path)
    args = parser.parse_args()
    records = {m['id']: m for m in json.loads(args.mesh_data.read_text())}
    bones = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'T1']
    levels = ['C4-C5', 'C5-C6', 'C6-C7']
    neural = [name for name in records if name == 'cord' or name.startswith('root-')]
    surfaces = {name: decode_triangles(m) for name, m in records.items()
                if name in bones + neural or m['name'] in ['Interbody Cage', 'Interbody Graft',
                                                              'Kerrison Rongeur', 'Vertebral artery']}
    for name in ('va-l', 'va-r'):
        surfaces[name] = decode_triangles(records[name])

    def verify(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0)):
        count = triangle_crossings(surfaces[a] + offset_a, surfaces[b] + offset_b)
        if count:
            raise ValueError(f'{a} crosses {b} ({count} triangle pairs)')

    def distraction_offsets(level, fraction):
        return dict(zip(level.split('-'), (.08 * fraction, -.055 * fraction)))

    count = 0
    for active, fraction in product(levels, np.linspace(0, 1, 5)):
        shifts = distraction_offsets(active, fraction)
        for name, bone in product(neural, bones):
            level = records[name].get('level')
            moved = max(0, shifts.get(level.split('-')[-1], 0)) if level and level != active else 0
            verify(name, bone, (0, moved, 0), (0, shifts.get(bone, 0), 0))
            count += 1

    for name, mesh in records.items():
        if mesh['name'] in ['Interbody Cage', 'Interbody Graft']:
            for body in mesh['level'].split('-'):
                verify(name, body)
                count += 1
        if 'fixation_tip' in mesh:
            if not contains(surfaces[mesh['fixation_body']], mesh['fixation_tip']):
                raise ValueError(f"{name} misses its designated bone {mesh['fixation_body']}")
            count += 1
        if mesh['name'] == 'Kerrison Rongeur':
            shifts = distraction_offsets(mesh['level'], 1)
            for progress, body in product(np.linspace(0, 1, 9), bones + neural + ['va-l', 'va-r']):
                offset = np.asarray(mesh['approach']) * (1 - progress)
                level = records[body].get('level')
                root_shift = max(0, shifts.get(level.split('-')[-1], 0)) if level and level != mesh['level'] else 0
                verify(name, body, offset, (0, shifts.get(body, root_shift), 0))
                count += 1

    print(f'Passed {count} sample pair and fixation checks.')
    print('Native C4 arterial overlap counts:', {
        side: triangle_crossings(surfaces['C4'], surfaces['va-' + side]) for side in ('l', 'r')
    })


if __name__ == '__main__':
    main()

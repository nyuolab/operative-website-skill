#!/usr/bin/env python3
"""Audit atlas fit and sampled motion. Write whole-step display rules from approved overlaps."""

import argparse
from collections import defaultdict
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from mesh_geometry import contains, decode_triangles, triangle_crossings


def pair(ids):
    a, b = ids
    if a == b:
        raise ValueError(f'Self-pair: {a}')
    return tuple(sorted((a, b)))


def posed_mesh(record, pose):
    if 'triangles' in pose:
        triangles = np.asarray(pose['triangles'], dtype=float).reshape(-1, 3, 3)
    else:
        triangles = record
    offset = np.asarray(pose.get('offset', [0, 0, 0]), dtype=float)
    if not np.isfinite(triangles).all() or offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError('Expected finite triangles and a finite 3D offset')
    return triangles + offset


def audit(records, plan):
    if not records or not any(plan.get(key) for key in ('restPairs', 'fixation', 'steps')):
        raise ValueError('Provide mesh records and at least one geometry check')
    source = {record['id']: decode_triangles(record) for record in records}
    if len(records) != len(source):
        raise ValueError('Duplicate mesh IDs')
    report = {'restCrossings': [], 'fixationFailures': [], 'motionCrossings': [], 'checkedFrames': 0}
    rules = {}
    for ids in plan.get('restPairs', []):
        a, b = pair(ids)
        count = triangle_crossings(source[a], source[b])
        if count:
            report['restCrossings'].append([a, b, count])
    for check in plan.get('fixation', []):
        bone = source[check['body']]
        if any(not contains(bone, point) for point in (check['tip'], *check.get('seatedPoints', []))):
            report['fixationFailures'].append(check)
    for step in plan.get('steps', []):
        key = step['key']
        if key in rules:
            raise ValueError(f'Duplicate step key: {key}')
        allowed = {pair(ids) for ids in step.get('contactPairs', [])}
        display = {pair(ids) for ids in step.get('hideStationaryPairs', [])}
        required = {pair(ids) for ids in step.get('checkPairs', [])}
        for ids in allowed | display | required:
            if any(name not in source for name in ids):
                raise ValueError(f'Unknown mesh in {key}: {ids}')
        if allowed & (display | required):
            raise ValueError(f'Intentional contact also requested as a clearance check in {key}')
        motions = defaultdict(set)
        frames = []
        for frame in step['frames']:
            if frame['progress'] != 'before' and not 0 <= frame['progress'] <= 1:
                raise ValueError(f'Invalid progress in {key}')
            meshes = {mesh_id: posed_mesh(source[mesh_id], pose)
                      for mesh_id, pose in frame['meshes'].items()}
            frames.append((frame['progress'], meshes))
            if frame['progress'] != 'before':
                for mesh_id, geometry in meshes.items():
                    motions[mesh_id].add(hashlib.sha256(geometry.round(6).tobytes()).digest())
        progress_values = {progress for progress, _ in frames}
        if len(progress_values) != len(frames) or not {0, 1} <= progress_values:
            raise ValueError(f'Include distinct start and end poses for {key}')
        if any(not meshes for progress, meshes in frames if progress in (0, 1)):
            raise ValueError(f'Start and end poses must include meshes in {key}')
        for a, b in allowed | display | required:
            if not any(a in meshes and b in meshes for _, meshes in frames):
                raise ValueError(f'Pair never appears together in {key}: {a}, {b}')
        moving = {mesh_id for mesh_id, poses in motions.items() if len(poses) > 1}
        hidden = set()
        for progress, meshes in frames:
            report['checkedFrames'] += 1
            bounds = {name: (verts.min(axis=(0, 1)), verts.max(axis=(0, 1)))
                      for name, verts in meshes.items() if len(verts)}
            for a, b in combinations(sorted(bounds), 2):
                ids = (a, b)
                if ids in allowed or not (ids in required or ids in display or a in moving or b in moving):
                    continue
                al, ah = bounds[a]
                bl, bh = bounds[b]
                if np.any(ah < bl) or np.any(bh < al):
                    continue
                count = triangle_crossings(meshes[a], meshes[b])
                if not count:
                    continue
                if ids in display and (a in moving) != (b in moving):
                    hidden.add((a, b) if a in moving else (b, a))
                else:
                    report['motionCrossings'].append([key, progress, a, b, count])
        rules[key] = sorted(hidden)
    return report, {key: pairs for key, pairs in rules.items() if pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--meshes', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--clearance-data', type=Path)
    args = parser.parse_args()
    report, rules = audit(json.loads(args.meshes.read_text()), json.loads(args.plan.read_text()))
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    unresolved = sum(len(report[key]) for key in ('restCrossings', 'fixationFailures', 'motionCrossings'))
    print(f"{report['checkedFrames']} frames, {sum(map(len, rules.values()))} display exclusions, {unresolved} unresolved checks")
    if unresolved:
        raise SystemExit(1)
    if args.clearance_data:
        args.clearance_data.write_text(json.dumps(rules, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()

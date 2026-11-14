"""Geometry primitives for atlas imports, landmark fitting, and mesh verification."""

import base64

import numpy as np


def transform_mesh(vertices, faces, world_matrix, region_matrix):
    """Apply column-vector affine matrices and correct winding for reflected meshes or curves."""
    vertices = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=int).reshape(-1, 3)
    transform = np.asarray(region_matrix) @ np.asarray(world_matrix)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices)
            or not np.isfinite(vertices).all() or not np.isfinite(transform).all()):
        raise ValueError('Expected finite 3D vertex coordinates and affine transforms')
    determinant = np.linalg.det(transform[:3, :3])
    if determinant == 0 or np.any(faces < 0) or np.any(faces >= len(vertices)):
        raise ValueError('Singular transform or invalid triangle indices')
    if determinant < 0:
        faces = faces[:, [0, 2, 1]]
    return vertices @ transform[:3, :3].T + transform[:3, 3], faces


def decode_triangles(record):
    """Read the interleaved position/normal buffer used by the website."""
    vertices = np.frombuffer(base64.b64decode(record['data'], validate=True), dtype='<f4')
    if (not record['count'] or vertices.size != record['count'] * 6
            or record['count'] % 3 or not np.isfinite(vertices).all()):
        raise ValueError(f"Invalid triangle buffer for {record['id']}")
    normals = vertices.reshape(-1, 6)[:, 3:]
    if not np.all(np.linalg.norm(normals, axis=1) > 0):
        raise ValueError(f"Zero normals in {record['id']}")
    return vertices.reshape(-1, 3, 6)[:, :, :3].astype(float)


def axis_crossings(triangles, axis, at):
    """Get sorted unique intersections of an axis-parallel line with a surface."""
    triangles = np.asarray(triangles, dtype=float)
    transverse = [i for i in range(3) if i != axis]
    flat = triangles[:, :, transverse]
    a, b = flat[:, 1] - flat[:, 0], flat[:, 2] - flat[:, 0]
    point = np.asarray(at) - flat[:, 0]
    det = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    valid = np.abs(det) > 1e-9
    inverse = np.divide(1., det, out=np.zeros_like(det), where=valid)
    u = (point[:, 0] * b[:, 1] - point[:, 1] * b[:, 0]) * inverse
    v = (a[:, 0] * point[:, 1] - a[:, 1] * point[:, 0]) * inverse
    inside = valid & (u >= -1e-8) & (v >= -1e-8) & (u + v <= 1 + 1e-8)
    q = triangles[:, :, axis]
    return np.unique((q[:, 0] + u * (q[:, 1] - q[:, 0]) + v * (q[:, 2] - q[:, 0]))[inside].round(6))


def contains(triangles, point):
    """Test strict interior for a closed surface, such as the intended fixation body."""
    point = np.asarray(point)
    for axis in range(3):
        hits = axis_crossings(triangles, axis, np.delete(point, axis))
        if len(hits) % 2 or np.any(np.abs(hits - point[axis]) < 1e-6):
            return False
        if np.searchsorted(hits, point[axis]) % 2 != 1:
            return False
    return True


def triangle_crossings(a, b):
    """Count triangle pairs with strict crossings. Shared edges and tangencies are allowed."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if not len(a) or not len(b):
        return 0
    al, ah = a.min(axis=1), a.max(axis=1)
    bl, bh = b.min(axis=1), b.max(axis=1)
    sa = np.all((ah >= bl.min(axis=0)) & (al <= bh.max(axis=0)), axis=1)
    sb = np.all((bh >= al.min(axis=0)) & (bl <= ah.max(axis=0)), axis=1)
    a, al, ah = a[sa], al[sa], ah[sa]
    b, bl, bh = b[sb], bl[sb], bh[sb]
    if len(a) > len(b):
        a, al, ah, b, bl, bh = b, bl, bh, a, al, ah
    count = 0
    for start in range(0, len(a), 128):
        low, high = al[start:start + 128], ah[start:start + 128]
        i, j = np.where(np.all((high[:, None] >= bl) & (low[:, None] <= bh), axis=2))
        if len(i):
            x, y = a[start + i], b[j]
            count += np.count_nonzero(edge_hits(x, y) | edge_hits(y, x))
    return int(count)


def edge_hits(edges, target):
    vertex = target[:, 0]
    a, b = target[:, 1] - vertex, target[:, 2] - vertex
    ends = np.roll(edges, -1, axis=1) - edges
    p = np.cross(ends, b[:, None, :])
    det = np.einsum('ijk,ik->ij', p, a)
    valid = np.abs(det) > 1e-9
    inv = np.divide(1., det, out=np.zeros_like(det), where=valid)
    t = edges - vertex[:, None, :]
    u = np.einsum('ijk,ijk->ij', t, p) * inv
    q = np.cross(t, a[:, None, :])
    v = np.einsum('ijk,ijk->ij', ends, q) * inv
    fraction = np.einsum('ijk,ik->ij', q, b) * inv
    return np.any(valid & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
                  & (fraction > 1e-5) & (fraction < 1 - 1e-5), axis=1)

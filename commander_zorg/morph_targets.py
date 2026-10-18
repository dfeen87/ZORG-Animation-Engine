"""Strict, position-only recipes bound to an immutable field and sorted IDs."""
from pathlib import Path
import re
import numpy as np
from .canonical import canonical_bytes, read_json, sha256, strict_json

LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,63}\Z', re.ASCII)


def label(value):
    if type(value) is not str or not LABEL.fullmatch(value):
        raise ValueError('label must be 1–64 ASCII letters/digits/underscores, starting with a letter')
    return value


def field_binding(scene):
    return sha256(canonical_bytes({'elements': [{'id': e.id, 'sigma': e.sigma,
        'weight': e.weight, 'home_xy': list(e.home_xy)} for e in scene.elements],
        'threshold': scene.threshold}))


def validate_target(doc, scene):
    doc = strict_json(canonical_bytes(doc))
    keys = {'schema_version','id','basis','element_ids','offsets','field_sha256','description','attribution'}
    if type(doc) is not dict or set(doc) != keys:
        raise ValueError('target: wrong fields')
    label(doc['id'])
    if doc['schema_version'] != 'cz-morph-target-0.1' or doc['basis'] != 'home-relative-world-half-height':
        raise ValueError('unsupported target contract/basis')
    if doc['element_ids'] != [e.id for e in scene.elements] or doc['field_sha256'] != field_binding(scene):
        raise ValueError('target element order or field binding differs')
    if any(type(doc[k]) is not str or not 1 <= len(doc[k]) <= 2000 for k in ('description','attribution')):
        raise ValueError('target description/attribution required')
    values = doc['offsets']
    if (type(values) is not list or len(values) != len(scene.elements) or
        any(type(row) is not list or len(row) != 2 or any(type(v) not in (int,float) for v in row) for row in values)):
        raise ValueError('target offsets must be numeric (elements,2)')
    offsets = np.array(values,dtype=np.float64)
    if (not np.isfinite(offsets).all() or np.any(np.linalg.norm(offsets,axis=1) > scene.max_displacement)
        or np.any(np.linalg.norm(scene.spring_k[:,None]*offsets,axis=1) > scene.max_total_force)):
        raise ValueError('target exceeds displacement or force budget')
    if doc['id'] == 'home' and np.any(offsets != 0):
        raise ValueError('home must retain original geometry')
    return doc


def load_targets(directory, scene):
    directory = Path(directory)
    targets = {}
    for path in sorted(directory.glob('*.json')):
        if path.is_symlink():
            raise ValueError('symlink recipe refused')
        doc = validate_target(read_json(path),scene)
        if path.stem != doc['id'] or doc['id'] in targets:
            raise ValueError('recipe filename/unique ID mismatch')
        targets[doc['id']] = doc
    if 'home' not in targets:
        raise ValueError('target library requires home')
    return targets

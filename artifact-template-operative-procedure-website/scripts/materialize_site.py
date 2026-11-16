#!/usr/bin/env python3
"""Copy the exact Pterional website and expose its editable inputs."""
import argparse
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.skill_dir.resolve() / 'assets/source'
    dest = args.output.resolve()
    if dest.exists():
        raise SystemExit('Choose a new empty project path; existing projects are never overwritten.')
    revision = json.loads((source / 'reference-revision.json').read_text())
    hashes = revision['referenceSha256']
    if not {'index.html', 'assets/app.js', 'assets/loader.js', 'assets/styles.css', 'data/manifest.json'} <= hashes.keys():
        raise SystemExit('The reference snapshot is missing required website files.')
    for name, expected in hashes.items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or not path.is_file():
            raise SystemExit(f'Invalid Pterional reference path: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Pterional reference differs from the pinned website: {name}')
    html = (source / 'index.html').read_text()
    loader_tags = list(re.finditer(
        r'<script defer src="assets/loader\.js" data-anatomy-chunks="([1-9][0-9]*)" '
        r'data-manifest-url="data/manifest\.json"></script>', html))
    if len(loader_tags) != 1:
        raise SystemExit('Unexpected reference loader tag; check its anatomy chunk count and manifest.')
    runtime_tag, chunk_count = loader_tags[0].group(0, 1)
    pieces = []
    for index in range(1, int(chunk_count) + 1):
        name = f'assets/anatomy-{index:02d}.bin'
        if name not in hashes:
            raise SystemExit(f'Unpinned anatomy chunk: {name}')
        pieces.append((source / name).read_bytes())
    meshes = json.loads(gzip.decompress(b''.join(pieces)))
    manifest = json.loads((source / 'data/manifest.json').read_text())
    if not isinstance(meshes, list) or len(meshes) != manifest['structure_count']:
        raise SystemExit('Retained anatomy and manifest counts disagree.')
    payloads = {'mesh-data': meshes, 'manifest-data': manifest, 'clearance-data': {}}
    runtime = (source / 'assets/app.js').read_text()
    stylesheet = '<link rel="stylesheet" href="assets/styles.css">'
    if html.count(stylesheet) != 1:
        raise SystemExit('Unexpected reference stylesheet.')
    # Inline the reference CSS for the offline and hosted packager.
    html = html.replace(stylesheet, '<style>\n' + (source / 'assets/styles.css').read_text() + '\n</style>')
    html = html.replace(runtime_tag, '<!-- GUIDE_DATA -->\n<!-- GUIDE_RUNTIME -->')
    html = re.sub(r'<div id="anatomy-loading".*?</div>', '', html, count=1, flags=re.S)
    html = re.sub(r'<noscript>.*?</noscript>', '', html, count=1, flags=re.S)
    for folder in ['src', 'data', 'research', 'static']:
        (dest / folder).mkdir(parents=True)
    shutil.copytree(source, dest / 'baseline')
    figures = source / 'assets/source-figures'
    if figures.is_dir():
        shutil.copytree(figures, dest / 'static/assets/source-figures')
    (dest / 'src/index.html').write_text(html)
    (dest / 'src/app.js').write_text(runtime)
    for key, value in payloads.items():
        (dest / 'data' / f'{key}.json').write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
    shutil.copy2(source / 'ATTRIBUTION.md', dest / 'ATTRIBUTION.md')
    shutil.copy2(source / 'reference-revision.json', dest / 'reference-revision.json')
    (dest / 'adaptation-status.json').write_text(json.dumps({
        'referenceCase': 'Pterional Craniotomy', 'status': 'unadapted reference',
        'required': 'Replace procedure content, sources, anatomy, masks, markers, instruments, laterality logic and all case-specific runtime branches before delivering another procedure.'
    }, indent=2))
    print(json.dumps({'project': str(dest), 'meshCount': len(meshes), 'dataIds': sorted(payloads),
                      'status': 'Editable reference copied; no new procedure has been generated.'}))


if __name__ == '__main__':
    main()

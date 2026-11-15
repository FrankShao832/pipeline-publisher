#!/usr/bin/env python3
"""Archive legacy dcc-segment publish dirs so the tree restarts department-keyed.

Why this exists
---------------
Until 2026-10-31 ``path_builder``'s ``department`` slot received a **DCC name**,
so publish trees contain ``<show>/<seq>/<shot>/{houdini,maya,nuke}/<type>/v###``.
Once publishing is department-keyed (``<shot>/fx/houdini/<type>/v###``), those
legacy version folders are invisible to the new tree — and worse, they look
like "the department has no history", so a fresh publish would silently restart
at v001 anyway while the old payload still sat on disk under an ambiguous key.

Decision (2026-10-31, Molei): **migrate, then restart numbering**. The legacy
payload is not treated as department history, so instead of re-keying files
(which would need a per-shot department guess and would carry v001-v003 into a
department that never owned them) the legacy dirs are moved out of the live
tree into ``<publish_root>/_legacy_dcc_<date>/`` preserving their relative path.
The live tree then starts clean at v001.

Safety
------
- dry-run by default; ``--apply`` performs the moves
- every move is a same-volume rename into the archive dir (reversible: move back)
- a TSV manifest (``action  src  dst  files``) is written; the reverse mapping
  is the rollback list
- idempotent: the archive dir is skipped when scanning, so a re-run finds 0 items

Usage
-----
    python3 tools/migrate_publish_vocab.py                 # dry run
    python3 tools/migrate_publish_vocab.py --apply         # do it
    python3 tools/migrate_publish_vocab.py --apply --archive-name _legacy_dcc_20261031
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publisher.core.constants import DEPARTMENT_DCC_MAP          # noqa: E402
from publisher.core.file_system.department_path import DCC_TOKENS  # noqa: E402

DEFAULT_PUBLISH_ROOT = '/Volumes/Development/projects/y_pipeline_publish'
DEFAULT_ARCHIVE = '_legacy_dcc_20261031'
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / 'plan' / 'publish_vocab_migration_20261031.tsv'

DEPARTMENT_TOKENS = frozenset(DEPARTMENT_DCC_MAP)


def _count_files(path: Path) -> int:
    return sum(1 for p in path.rglob('*') if p.is_file())


def find_legacy_dirs(publish_root: Path, archive_name: str) -> list:
    """Return dcc-named dirs that occupy a *department* slot.

    A dcc token is legitimate as an inner segment (``fx/houdini``) but illegal
    directly under a shot (``demo_shot/houdini``). The parent's name is what
    tells the two apart: a department name means the nesting is correct.
    """
    found = []
    for path in sorted(publish_root.rglob('*')):
        if not path.is_dir():
            continue
        if archive_name in path.parts:
            continue
        if path.name.lower() not in DCC_TOKENS:
            continue
        if path.parent.name.lower() in DEPARTMENT_TOKENS:
            continue          # legit <dept>/<dcc> nesting
        if path.parent.name.lower() in DCC_TOKENS:
            continue          # nested under another dcc — handled with its parent
        found.append(path)
    return found


def plan(publish_root: Path, archive_dir: Path, archive_name: str) -> list:
    rows = []
    for src in find_legacy_dirs(publish_root, archive_name):
        dst = archive_dir / src.relative_to(publish_root)
        rows.append({
            'action': 'move',
            'src': src,
            'dst': dst,
            'files': _count_files(src),
        })
    return rows


def write_manifest(rows: list, manifest: Path, applied: bool) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    header = 'action\tsrc\tdst\tfiles\tstatus\n'
    status = 'moved' if applied else 'planned'
    body = ''.join(
        f"{r['action']}\t{r['src']}\t{r['dst']}\t{r['files']}\t{status}\n" for r in rows
    )
    manifest.write_text(header + body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--publish-root', default=DEFAULT_PUBLISH_ROOT)
    ap.add_argument('--archive-name', default=DEFAULT_ARCHIVE)
    ap.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    ap.add_argument('--apply', action='store_true', help='perform the moves')
    args = ap.parse_args()

    publish_root = Path(args.publish_root)
    if not publish_root.is_dir():
        print(f'ERROR: publish root not found: {publish_root}')
        return 2

    archive_dir = publish_root / args.archive_name
    rows = plan(publish_root, archive_dir, args.archive_name)

    if not rows:
        print('Nothing to migrate — live tree is already department-keyed.')
        return 0

    total_files = sum(r['files'] for r in rows)
    print(f'{"MOVE" if args.apply else "PLAN"}: {len(rows)} legacy dir(s), {total_files} file(s)')
    for r in rows:
        rel_src = r['src'].relative_to(publish_root)
        print(f"  {rel_src}  ->  {r['dst'].relative_to(publish_root)}  ({r['files']} files)")

    write_manifest(rows, Path(args.manifest), applied=args.apply)
    print(f'manifest: {args.manifest}')

    if not args.apply:
        print('\nDry run — nothing moved. Re-run with --apply.')
        return 0

    for r in rows:
        r['dst'].parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(r['src']), str(r['dst']))

    leftovers = plan(publish_root, archive_dir, args.archive_name)
    print(f'\nMoved {len(rows)} dir(s). Re-scan finds {len(leftovers)} remaining.')
    return 0 if not leftovers else 1


if __name__ == '__main__':
    raise SystemExit(main())

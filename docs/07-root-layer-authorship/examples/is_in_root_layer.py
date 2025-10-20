#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
List prims authored in the current stage's root layer.

Examples (PowerShell):
  python .\docs\07-root-layer-authorship\examples\is_in_root_layer.py --file .\path\to\shot.usda
  python .\docs\07-root-layer-authorship\examples\is_in_root_layer.py --file .\path\to\shot.usda --root /World/Looks --type Material

Requires USD Python (pxr). Install via conda: conda install -c conda-forge usd
"""
from __future__ import annotations
import argparse
from typing import Optional

from pxr import Usd


def is_in_root_layer(stage: Usd.Stage, prim: Usd.Prim) -> bool:
    """Return True if the prim has a PrimSpec in the current stage's root layer."""
    root_id = stage.GetRootLayer().identifier
    try:
        for spec in prim.GetPrimStack():
            if spec.layer.identifier == root_id:
                return True
    except Exception:
        pass
    return False


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="List prims authored in root layer")
    parser.add_argument('--file', required=True, help='Path to USD file')
    parser.add_argument('--root', default=None, help='Start traversal from this prim path (default: pseudo-root)')
    parser.add_argument('--type', default=None, help='Optional type name filter, e.g. Material, Xform, Mesh')
    args = parser.parse_args(argv)

    stage = Usd.Stage.Open(args.file)
    if not stage:
        print(f"ERROR: cannot open {args.file}")
        return 1

    start = stage.GetPrimAtPath(args.root) if args.root else stage.GetPseudoRoot()
    if not start or not start.IsValid():
        print(f"ERROR: invalid start prim: {args.root}")
        return 2

    count = 0
    for prim in stage.Traverse():
        if args.type and prim.GetTypeName() != args.type:
            continue
        if is_in_root_layer(stage, prim):
            print(prim.GetPath())
            count += 1

    print(f"Total prims authored in root layer: {count}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

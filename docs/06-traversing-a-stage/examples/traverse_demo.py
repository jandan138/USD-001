#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Traverse a USD stage with optional predicates and modes.

Usage (PowerShell):
  python .\docs\06-traversing-a-stage\examples\traverse_demo.py --file .\path\to\car.usda
  python .\docs\06-traversing-a-stage\examples\traverse_demo.py --file .\path\to\car.usda --root /World/Car --active-loaded-only --prepost

Requirements:
  - USD Python bindings (pxr). For Conda: `conda install -c conda-forge usd`
"""
from __future__ import annotations
import argparse
import sys
from typing import Optional

try:
    from pxr import Usd
except Exception as exc:  # pragma: no cover
    print("ERROR: pxr (USD Python bindings) not found. Install via conda-forge: conda install -c conda-forge usd", file=sys.stderr)
    raise


def build_predicate(active_loaded_only: bool) -> Usd.PrimFlagsPredicate:
    predicate = Usd.PrimIsDefined
    if active_loaded_only:
        predicate = predicate & Usd.PrimIsActive & Usd.PrimIsLoaded
    return predicate


def traverse(stage: Usd.Stage, root_path: Optional[str], predicate: Usd.PrimFlagsPredicate, prepost: bool) -> None:
    root = stage.GetPrimAtPath(root_path) if root_path else stage.GetPseudoRoot()
    if not root or not root.IsValid():
        print(f"ERROR: Invalid root prim path: {root_path}")
        sys.exit(2)

    if prepost:
        rng = Usd.PrimRange.PreAndPostVisit(root, predicate=predicate)
        it = iter(rng)
        while True:
            try:
                prim = next(it)
            except StopIteration:
                break
            phase = 'post' if it.IsPostVisit() else 'pre'
            print(f"[{phase}] {prim.GetPath()}")
    else:
        for prim in Usd.PrimRange(root, predicate=predicate):
            print(prim.GetPath())


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Traverse a USD stage")
    parser.add_argument('--file', required=True, help='Path to a USD file (.usd/.usda/.usdc)')
    parser.add_argument('--root', default=None, help='Root prim path to start traversal (default: pseudo-root)')
    parser.add_argument('--active-loaded-only', action='store_true', help='Filter to active & loaded & defined prims')
    parser.add_argument('--prepost', action='store_true', help='Use PreAndPostVisit to distinguish pre/post visits')

    args = parser.parse_args(argv)

    stage = Usd.Stage.Open(args.file)
    if not stage:
        print(f"ERROR: Failed to open USD file: {args.file}")
        return 1

    predicate = build_predicate(args.active_loaded_only)
    traverse(stage, args.root, predicate, args.prepost)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

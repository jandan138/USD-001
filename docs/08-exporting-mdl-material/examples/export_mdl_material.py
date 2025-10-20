#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export a single MDL Material into a new USD stage, rewriting asset paths.

Examples (PowerShell):
  python .\docs\08-exporting-mdl-material\examples\export_mdl_material.py --in .\path\to\shot.usda --mat /World/Looks/MyMat --out .\export\MyMat.usda
  python .\docs\08-exporting-mdl-material\examples\export_mdl_material.py --in .\path\to\shot.usda --mat /World/Looks/MyMat --out .\export\MyMat.usda --assets-path-mode absolute

Requires USD Python bindings (pxr): conda install -c conda-forge usd
"""
from __future__ import annotations
import argparse
import os
from typing import Optional

from pxr import Sdf, Usd, UsdShade


def _anchor_dir_for_attr(attr: Usd.Attribute) -> Optional[str]:
    """Return the directory that should be used as the anchor for resolving an attribute's asset paths.

    We inspect the property's stack and take the strongest authored spec's layer realPath/identifier.
    """
    try:
        for spec in attr.GetPropertyStack():  # strongest to weakest
            layer = spec.layer
            if layer.realPath:
                return os.path.dirname(layer.realPath)
            if layer.identifier:
                return os.path.dirname(layer.identifier)
    except Exception:
        pass
    return None


def _resolve_abs_path(anchor_dir: Optional[str], path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if os.path.isabs(path):
        return os.path.normpath(path)
    if anchor_dir:
        return os.path.normpath(os.path.join(anchor_dir, path))
    return None


def _export_mdl_material(new_stage: Usd.Stage, new_mat: UsdShade.Material, mdl_shader_src: UsdShade.Shader, assets_path_mode: str = "relative") -> None:
    # 1) create mdlShader under the new material
    parent = new_mat.GetPath().pathString
    shader_path = f"{parent}/mdlShader"
    mdl_new = UsdShade.Shader.Define(new_stage, shader_path)

    # 2) copy info:id
    src_prim = mdl_shader_src.GetPrim()
    id_attr = src_prim.GetAttribute("info:id")
    if id_attr and id_attr.HasAuthoredValue():
        mdl_new.CreateIdAttr(id_attr.Get())
    else:
        mdl_new.CreateIdAttr("mdlMaterial")

    # 3) copy info:mdl:* and implementation hints; rewrite AssetPath
    new_dir_layer = new_stage.GetRootLayer()
    new_dir = os.path.dirname(new_dir_layer.realPath or new_dir_layer.identifier)
    for name in src_prim.GetPropertyNames():
        if name.startswith("info:mdl:") or name in ("info:implementationSource", "info:sourceAsset"):
            a_src = src_prim.GetAttribute(name)
            if not a_src or not a_src.HasAuthoredValue():
                continue
            v = a_src.Get()
            if isinstance(v, Sdf.AssetPath):
                anchor_dir = _anchor_dir_for_attr(a_src)
                p = v.resolvedPath or v.path
                abs_path = _resolve_abs_path(anchor_dir, p) if p else None
                if abs_path:
                    if assets_path_mode == "absolute":
                        v = Sdf.AssetPath(abs_path)
                    else:
                        rel = os.path.relpath(abs_path, new_dir).replace("\\", "/")
                        v = Sdf.AssetPath(rel)
            a_dst = mdl_new.GetPrim().CreateAttribute(name, a_src.GetTypeName())
            a_dst.Set(v)

    # 4) create outputs:surface (MDL)
    mdl_new.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    # 5) copy inputs:* (with AssetPath rewrite)
    mdl_sa_attr = src_prim.GetAttribute("info:mdl:sourceAsset")
    mdl_anchor_dir = _anchor_dir_for_attr(mdl_sa_attr) if mdl_sa_attr else None
    for inp in mdl_shader_src.GetInputs():
        i_dst = mdl_new.CreateInput(inp.GetBaseName(), inp.GetTypeName())
        try:
            val = inp.Get()
            if isinstance(val, Sdf.AssetPath):
                attr = src_prim.GetAttribute(f"inputs:{inp.GetBaseName()}")
                anchor_dir = _anchor_dir_for_attr(attr) if attr else None
                if not anchor_dir:
                    anchor_dir = mdl_anchor_dir
                p = (val.resolvedPath or val.path) if val else None
                abs_path = _resolve_abs_path(anchor_dir, p) if p else None
                if abs_path:
                    if assets_path_mode == "absolute":
                        i_dst.Set(Sdf.AssetPath(abs_path))
                    else:
                        rel = os.path.relpath(abs_path, new_dir).replace("\\", "/")
                        i_dst.Set(Sdf.AssetPath(rel))
                else:
                    i_dst.Set(val)
            else:
                if val is not None:
                    i_dst.Set(val)
        except Exception:
            pass

    # 6) connect material outputs:surface:mdl
    out_mdl = new_mat.GetSurfaceOutput("mdl") or new_mat.CreateSurfaceOutput("mdl")
    out_mdl.ConnectToSource(mdl_new.GetOutput("surface"))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export a single MDL material to a new USD stage")
    parser.add_argument('--in', dest='inp', required=True, help='Source USD file path')
    parser.add_argument('--mat', dest='mat_path', required=True, help='Material prim path in source stage')
    parser.add_argument('--shader', dest='shader_path', default=None, help='Optional MDL shader prim path (auto-detected if omitted)')
    parser.add_argument('--out', dest='outp', required=True, help='Output USD file path (.usda recommended)')
    parser.add_argument('--assets-path-mode', choices=['relative','absolute'], default='relative', help='How to write asset paths in the exported file')
    args = parser.parse_args(argv)

    # 1) open source stage
    src_stage = Usd.Stage.Open(args.inp)
    if not src_stage:
        print(f"ERROR: cannot open {args.inp}")
        return 1

    mat_prim = src_stage.GetPrimAtPath(args.mat_path)
    if not mat_prim or not mat_prim.IsValid():
        print(f"ERROR: invalid material prim path: {args.mat_path}")
        return 2

    material = UsdShade.Material(mat_prim)
    if not material:
        print("ERROR: prim is not a UsdShade.Material")
        return 3

    # 2) find MDL shader
    mdl_shader = None
    if args.shader_path:
        sp = src_stage.GetPrimAtPath(args.shader_path)
        if sp and sp.IsValid():
            mdl_shader = UsdShade.Shader(sp)
    else:
        out = material.GetSurfaceOutput("mdl")
        if out and out.HasConnectedSource():
            source = out.GetConnectedSource()
            # source is a tuple (connectableAPI, outputName, sourceType)
            mdl_shader = UsdShade.Shader(source[0].GetPrim())

    if not mdl_shader:
        print("ERROR: cannot locate MDL shader (try --shader)")
        return 4

    # 3) create new stage to export
    out_layer = Sdf.Layer.CreateNew(args.outp)
    if not out_layer:
        print(f"ERROR: cannot create output: {args.outp}")
        return 5

    new_stage = Usd.Stage.Open(out_layer.identifier)

    # define a minimal hierarchy and the target material
    root = Usd.Stage.Open(out_layer.identifier)
    world = root.DefinePrim('/World', 'Xform')
    looks = root.DefinePrim('/World/Looks', 'Scope')
    new_mat = UsdShade.Material.Define(root, '/World/Looks/ExportedMat')

    # 4) export
    _export_mdl_material(root, new_mat, mdl_shader, assets_path_mode=args.assets_path_mode)

    # set default prim for niceness
    root.SetDefaultPrim(world)

    # save
    root.GetRootLayer().Save()
    print(f"Exported to: {args.outp}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a minimal "bed" scene and bind materials to its parts.

Usage (PowerShell):
  python .\docs\09-binding-materials\examples\make_bed_bindings.py --out .\export\bed_bound.usda

Requires: USD Python (pxr)
"""
from __future__ import annotations
import argparse
from typing import Optional

from pxr import Sdf, Usd, UsdGeom, UsdShade


def _define_minimal_mesh(stage: Usd.Stage, path: str) -> UsdGeom.Mesh:
    """Define a tiny quad mesh (placeholder) just to visualize binding."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    # Minimal 2x2 quad as two triangles
    mesh.CreatePointsAttr([(0,0,0), (1,0,0), (1,0,1), (0,0,1)])
    mesh.CreateFaceVertexCountsAttr([3,3])
    mesh.CreateFaceVertexIndicesAttr([0,1,2, 0,2,3])
    return mesh


def build_stage(outp: str) -> None:
    layer = Sdf.Layer.CreateNew(outp)
    stage = Usd.Stage.Open(layer.identifier)

    # hierarchy
    world = stage.DefinePrim('/Bed', 'Xform')
    geom = stage.DefinePrim('/Bed/Geom', 'Xform')
    looks = stage.DefinePrim('/Bed/Looks', 'Scope')

    # meshes
    frame = _define_minimal_mesh(stage, '/Bed/Geom/Frame')
    mattress = _define_minimal_mesh(stage, '/Bed/Geom/Mattress')

    # materials + MDL shaders (dummy values)
    wood_mat = UsdShade.Material.Define(stage, '/Bed/Looks/BedWood')
    wood_shader = UsdShade.Shader.Define(stage, '/Bed/Looks/BedWood/mdlShader')
    wood_shader.CreateIdAttr('mdlMaterial')
    wood_shader.GetPrim().CreateAttribute('info:mdl:sourceAsset', Sdf.ValueTypeNames.Asset)
    wood_shader.CreateOutput('surface', Sdf.ValueTypeNames.Token)
    wood_shader.CreateInput('base_color', Sdf.ValueTypeNames.Color3f).Set((0.45, 0.30, 0.18))
    wood_mat.CreateSurfaceOutput('mdl').ConnectToSource(wood_shader.GetOutput('surface'))

    fabric_mat = UsdShade.Material.Define(stage, '/Bed/Looks/BedFabric')
    fabric_shader = UsdShade.Shader.Define(stage, '/Bed/Looks/BedFabric/mdlShader')
    fabric_shader.CreateIdAttr('mdlMaterial')
    fabric_shader.GetPrim().CreateAttribute('info:mdl:sourceAsset', Sdf.ValueTypeNames.Asset)
    fabric_shader.CreateOutput('surface', Sdf.ValueTypeNames.Token)
    fabric_shader.CreateInput('base_color', Sdf.ValueTypeNames.Color3f).Set((0.80, 0.80, 0.85))
    fabric_mat.CreateSurfaceOutput('mdl').ConnectToSource(fabric_shader.GetOutput('surface'))

    # bindings
    UsdShade.MaterialBindingAPI(frame.GetPrim()).Bind(wood_mat)
    UsdShade.MaterialBindingAPI(mattress.GetPrim()).Bind(fabric_mat)

    stage.SetDefaultPrim(world)
    stage.GetRootLayer().Save()
    print(f"Saved to {outp}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description='Build a minimal bed with material bindings')
    p.add_argument('--out', required=True, help='Output .usda path')
    args = p.parse_args(argv)
    build_stage(args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

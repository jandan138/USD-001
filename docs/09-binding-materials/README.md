# Module 9: 把材质应用到几何体（以“床”为例）

目标：让一个“实在的物体”（例如一张床）拥有外观。我们用 `UsdShade.Material` + `UsdShade.Shader` 定义材质，然后把材质绑定（binding）到几何体上。

---

## 1. 三者关系总览

- 几何体（Geometry）：如 `UsdGeom.Mesh`、`Xform` 之下的模型层级，描述了形状、拓扑、法线、UV 等。
- 材质（Material）：`UsdShade.Material`，对外暴露 `outputs:surface:*` 并连接到一个 Shader 的输出。
- 着色器（Shader）：`UsdShade.Shader`，例如 MDL Shader，提供 `outputs:surface` 等端口。

关系：
- 几何体不直接“知道” Shader；几何体绑定的是 Material。
- Material 通过连接把自己的 `outputs:surface:*` 指向某个 Shader 的 `outputs:surface`。
- 渲染器沿着“几何体 → 绑定的 Material → Material 输出连接的 Shader”这条链找到最终外观。

---

## 2. 一个“床”资产的典型 USD 结构

假设有一个床资产 `bed.usda`：

```usda
#usda 1.0
(
    defaultPrim = "Bed"
)

def Xform "Bed"
{
    def Xform "Geom"
    {
        def Mesh "Frame" { /* 网格数据（points/faceVertexIndices/UVs...）*/ }
        def Mesh "Mattress" { /* ... */ }
        def Mesh "Pillow" { /* ... */ }
    }

    def Scope "Looks"
    {
        def Material "BedWood"
        {
            token outputs:surface:mdl.connect = "/Bed/Looks/BedWood/mdlShader.outputs:surface"
            def Shader "mdlShader"
            {
                uniform token info:id = "mdlMaterial"
                asset info:mdl:sourceAsset = @materials/wood.mdl@
                token outputs:surface
                color3f inputs:base_color = (0.45, 0.30, 0.18)
            }
        }
        def Material "BedFabric" { /* 类似结构，连接到织物 MDL Shader */ }
    }
}
```

- `Geom` 里放形状；`Looks` 里放材质与着色器。
- `BedWood` 与 `BedFabric` 是两个 `UsdShade.Material`，各自连接到一个 MDL Shader。

---

## 3. 绑定：让几何体“用上”材质

在 USD 中，绑定关系写在几何体 Prim 上（或祖先）：

```usda
def Mesh "Frame"
{
    rel material:binding = </Bed/Looks/BedWood>
}

def Mesh "Mattress"
{
    rel material:binding = </Bed/Looks/BedFabric>
}
```

- `material:binding` 是一个关系（relationship），指向 `UsdShade.Material` 的 Prim 路径。
- 渲染时，`Frame` 会使用 `BedWood` 材质的外观，`Mattress` 使用 `BedFabric`。

Python 绑定示例：

```python
from pxr import UsdShade, UsdGeom
frame = UsdGeom.Mesh.Get(stage, '/Bed/Geom/Frame')
fabric = UsdShade.Material.Get(stage, '/Bed/Looks/BedFabric')
UsdShade.MaterialBindingAPI(frame.GetPrim()).Bind(fabric)
```

---

## 4. 引用、复用与覆盖（Reference / Variant / Override）

一个常见工作流：
- 资产文件 `bed.usda` 定义结构和默认材质。
- 镜头文件 `shot.usda` 通过 `reference` 引用 `bed.usda`：

```usda
def Xform "BedA"
{
    payload = @./assets/bed.usda@
}
```

- 在镜头文件里你可以对引用的实例做“覆盖”（override），比如重新绑定材质（换不同颜色/布料）：

```usda
over "BedA/Geom/Frame"
{
    rel material:binding = </World/Looks/BlackWood>
}
```

> 提示：这也是为什么第 7 章里会讲“根层作者性（Root Layer Authorship）”。当你只想导出“当前文件亲自修改过”的材质绑定/材质定义时，就需要识别它是否在根层有作者条目。

---

## 5. 每面（per-face）绑定（高级）

USD 支持 per-face 材质：
- 方式一：把一个 Mesh 拆成多个 `GeomSubset`，给每个 subset 绑定不同材质。
- 方式二：使用 `material:binding:collection` 与集合（Collections）实现按集合绑定。

示例（GeomSubset）：

```usda
def Mesh "Mattress"
{
    # ... mesh data ...
    def GeomSubset "Top"
    {
        uniform token elementType = "face"
        int[] indices = [0, 1, 2, 3, ...]  # 顶面三角面的索引
        rel material:binding = </Bed/Looks/BedFabric>
    }
}
```

---

## 6. 完整 Python 演练（构建最小床 + 绑定）

示例脚本位置：`examples/make_bed_bindings.py`。
- 创建 `/Bed` 层级与几个 Mesh（省略网格数据，演示结构即可）。
- 创建两个 Material + MDL Shader。
- 给 `Frame` 绑定木头材质，给 `Mattress` 绑定布料材质。
- 保存为 `.usda` 以便在 `usdview` 中查看。

运行（PowerShell）：
```powershell
python .\docs\09-binding-materials\examples\make_bed_bindings.py --out .\export\bed_bound.usda
```

---

## 7. FAQ（围绕“床”）
- 床这个 usd 需要包含什么？
  - 至少：形状（Mesh/Xform 层级）、材质（Material + Shader）、以及绑定（写在 Mesh 或祖先上）。还可以包含 UV、法线、材质参数、贴图路径等。
- Shader 和床 usd 的关系？
  - Shader 是一个 Prim（通常放在 `Looks`/材质层级下），通过 Material 输出连接到 Shader；床（几何体）通过 `material:binding` 关系绑定到 Material。
- 我只有 `obj/fbx`，怎么变成上面结构？
  - 用 DCC（Maya/Blender/Omniverse 等）或脚本导出为 USD；在导出流程里建立 Looks（材质）与绑定；也可在导出后用脚本补齐。

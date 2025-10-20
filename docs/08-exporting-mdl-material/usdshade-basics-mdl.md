# UsdShade 入门：以 MDL 为例（超新手友好）

本文是第 8 章的补充读物：从 0 讲清 UsdShade 的基本概念，并以 MDL 材质为例，演示 Material/Shader 的关系、端口（inputs/outputs）、元数据（info:id、info:mdl:*）以及如何把材质绑定到几何体。

---

## 1. 我需要先知道的名词

- Material（材质）：一个“着色集合”，对外暴露若干输出（如 `outputs:surface:*`）。
- Shader（着色器节点）：实际计算表面/体积/灯光外观的节点。不同实现有不同 “id”（`info:id`）。
- 输入与输出：
  - 输入（`inputs:*`）是参数，如颜色、粗糙度、贴图路径等。
  - 输出（`outputs:*`）是结果端口，例如 `outputs:surface`（表面着色结果）。
- 连接（Connection）：把一个输出接到另一个输入（或 Material 的输出），就建立了依赖关系。
- MDL：一种材质定义语言（NVIDIA）。在 USD 里，MDL 作为一种 Shader 类型存在。

---

## 2. 几个关键规则（简记）

- `UsdShade.Material` 不直接“算颜色”，它通过连接某个 `UsdShade.Shader` 的输出作为自己的输出。
- `info:id` 决定了 Shader 的“实现类型”。MDL Shader 常见值：`mdlMaterial`。
- MDL 相关的元数据常放在 `info:mdl:*` 命名空间（例如 `info:mdl:sourceAsset` 指向 .mdl 文件）。
- Material 的表面输出口通常是 `outputs:surface:<renderContext>`，例如：
  - `outputs:surface:mdl`（给 MDL 渲染上下文）
  - `outputs:surface:universal`（通用输出，取决于流水线）

---

## 3. 最小可用 USD 示例（.usda）

下面是一个极简的结构，描述了一个 Material 和一个 MDL Shader，并把二者连起来：

```usda
#usda 1.0
(
    defaultPrim = "World"
)

def Xform "World"
{
    def Scope "Looks"
    {
        def Material "MyMat"
        {
            token outputs:surface:mdl.connect = "/World/Looks/MyMat/mdlShader.outputs:surface"

            def Shader "mdlShader"
            {
                uniform token info:id = "mdlMaterial"
                asset info:mdl:sourceAsset = @materials/library.mdl@
                token outputs:surface

                # 示例输入参数（不同 MDL 实现会有不同的 inputs）
                color3f inputs:base_color = (0.8, 0.2, 0.2)
                float inputs:roughness = 0.3
            }
        }
    }
}
```

要点：
- `Material.outputs:surface:mdl` 连接到 `mdlShader.outputs:surface`。
- `mdlShader` 有 `info:id = "mdlMaterial"` 表示这是 MDL 类型。
- `info:mdl:sourceAsset` 指向某个 `.mdl` 文件（这里展示为逻辑路径 `@materials/library.mdl@`）。

---

## 4. 用 Python 构建同样的结构

```python
from pxr import Usd, Sdf, UsdShade

# 新建一个 Stage
stage = Usd.Stage.CreateInMemory()
world = stage.DefinePrim('/World', 'Xform')
looks = stage.DefinePrim('/World/Looks', 'Scope')
mat = UsdShade.Material.Define(stage, '/World/Looks/MyMat')

# 定义 MDL Shader
shader = UsdShade.Shader.Define(stage, '/World/Looks/MyMat/mdlShader')
shader.CreateIdAttr('mdlMaterial')  # 等效于 info:id = "mdlMaterial"
shader.GetPrim().CreateAttribute('info:mdl:sourceAsset', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('materials/library.mdl'))
shader.CreateOutput('surface', Sdf.ValueTypeNames.Token)

# 示例参数
shader.CreateInput('base_color', Sdf.ValueTypeNames.Color3f).Set((0.8, 0.2, 0.2))
shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.3)

# 把 Material 的 surface:mdl 接到 Shader 的 surface 输出
mat.CreateSurfaceOutput('mdl').ConnectToSource(shader.GetOutput('surface'))

# 默认 prim & 预览
stage.SetDefaultPrim(world)
print(stage.GetRootLayer().ExportToString())
```

---

## 5. 给几何体绑定材质（Binding）

要把材质“用”到几何体上，需要绑定：

```python
from pxr import UsdGeom

mesh = UsdGeom.Mesh.Define(stage, '/World/Geom/Plane')
# ... 这里可以设置顶点、法线、UV 等

# 绑定：把材质应用到这个 prim
UsdShade.MaterialBindingAPI(mesh.GetPrim()).Bind(mat)
```

注意：
- 绑定关系写在几何体 prim 上（或其祖先）
- 渲染器据此查找被绑定的 Material，并解析它的输出连接

---

## 6. 常见问题（FAQ）

- 为什么我的贴图找不到？
  - 多半是路径基准（anchor）问题。请参考第 8 章关于 AssetPath 重定位的内容。
- `info:id` 填什么？
  - 取决于你使用的渲染上下文/插件。MDL 示例一般使用 `mdlMaterial`。
- `outputs:surface:mdl` 一定要有 `:mdl` 吗？
  - 渲染上下文名称依流水线而定；有的会使用 `:mdl`、有的使用 `:universal` 或其它 token。关键是与渲染器的约定匹配。

---

## 7. 进一步阅读
- 本仓库：`docs/08-exporting-mdl-material/README.md`（资源路径重定位与导出流程）
- UsdShade Schema 文档（了解 Material/Shader/NodeGraph 的完整能力）
- 你所用渲染器/插件的文档（确认 `info:id` 与上下文约定）

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

---

## 8. 补充：Shader 是 Prim 还是 Material 的属性？`info:mdl:sourceAsset` 在哪里？`info` 是什么？

简短结论：
- Shader 本质上是一个 Prim（一个独立的 scenegraph 节点），而不是 Material 的“属性”。
- `info:mdl:sourceAsset` 是放在 Shader 的 Prim 或 Shader 的属性上（通常在 Shader 的 `info:` 命名空间下），也有可能出现在与实现相关的元数据层级中（例如在某些管线会把实现元信息放在 Material 层级），但常见且推荐的做法是把实现相关的 `info:mdl:*` 放在 Shader 所在的 Prim 的属性上。
- `info:` 只是一个命名空间前缀，用来组织元数据（metadata / implementation hints），它并不是 USD 的特殊类型，而是一个习惯性的命名约定用于区分 "语义" 数据（如 transform、geometry）与 "实现/元" 数据（如 shader 实现、asset 路径）。

详细解释：

- Shader 是 Prim：
  - 在 USD 场景图中，每个节点（如 Xform、Mesh、Material、Shader）都以 Prim 表示。你可以用 `UsdShade.Shader.Define(stage, '/World/Looks/MyMat/mdlShader')` 在场景树上创建一个 Shader Prim。
  - Shader Prim 上可以有属性（attributes），例如 `info:id`、`inputs:base_color`、`outputs:surface`。这些属性就是该 Prim 的数据。

- Material 与 Shader 的关系：
  - `UsdShade.Material` 代表材质（一个容器/高层抽象），它通常不会直接包含复杂的实现细节，而是通过 `outputs:surface:*` 等端口连接到某个 Shader Prim 的输出。
  - 这种连接是通过 USD 的连接机制实现（`ConnectToSource`），并非把 Shader 作为 Material 的“子属性”。不过，实践中人们常把 Shader 放在 Material 的子路径下（例如 `/World/Looks/MyMat/mdlShader`），这样从组织上看起来像“属于”这个 Material，但在 USD 的数据模型上，Shader 仍是一个独立的 Prim。

- `info:` 命名空间：
  - `info:` 前缀只是一个用于属性命名的惯例，用来表示该属性是“元数据/实现提示”（implementation hint）而非渲染语义（如 geometry 点坐标）。
  - 常见的 `info:` 属性包括 `info:id`（指定 shader 实现类型）、`info:implementationSource`、`info:sourceAsset`、`info:mdl:sourceAsset` 等。
  - 这些属性的读取/解释通常是由渲染器插件或上层工具来完成：USD 本身不会强制解释 `info:` 下的内容。

- `info:mdl:sourceAsset` 应该放在哪里？
  - 推荐做法：把 `info:mdl:sourceAsset` 放在提供实现的 Shader Prim 上（例如 `MyMat/mdlShader` 的 Prim）。这样，查看 Shader 的人或自动化工具可以直接在该 Prim 上找到实现的 `.mdl` 文件路径。
  - 也有一些项目把实现元数据放在 Material 级别，但这会导致工具在查找实际实现时需要额外的约定或索引来找到对应的 Shader。为简单和一致，建议常把 `info:mdl:*` 放到 Shader 上。

示例：

```usda
def Material "MyMat"
{
    token outputs:surface:mdl.connect = "/World/Looks/MyMat/mdlShader.outputs:surface"

    def Shader "mdlShader"
    {
        uniform token info:id = "mdlMaterial"
        asset info:mdl:sourceAsset = @materials/library.mdl@
        token outputs:surface
    }
}
```

在这个例子里：
- `mdlShader` 是一个 Shader Prim；
- `info:mdl:sourceAsset` 是在 Shader Prim 上定义的属性，指向实际的 `.mdl` 文件；
- `Material.outputs:surface:mdl` 只是一个连接点，指向 Shader 的 `outputs:surface` 输出。

小贴士：
- 当你在代码里查找 MDL 实现时，优先在 Shader Prim 上查找 `info:mdl:*`；如果找不到，再检查 Material 级别（视项目约定而定）。

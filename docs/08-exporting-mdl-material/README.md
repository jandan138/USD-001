# Module 8: Exporting an MDL Material（导出 MDL 材质）

本章把一段“看起来很工程化”的导出函数，拆成适合新手理解的小步骤：先讲背景，再逐行解释它做了什么、为什么要这么做，以及如何亲手跑通一个示例脚本。

---

## 1. 背景补全：USD / UsdShade / MDL / Attribute / AssetPath

- USD（Universal Scene Description）
  - 用“Stage（场景视图）+ 多个 Layer（图层文件）”组成一个最终场景。
  - Stage 负责合成、读写；Layer 是实际的 `.usd/.usda/.usdc` 文件。
- UsdShade（USD 的着色系统）
  - 用 `UsdShade.Material` 表示材质，用 `UsdShade.Shader` 表示着色器节点。
  - `Material` 的 `outputs:surface:*` 通常连接到某个 `Shader` 的 `outputs:surface`。
- MDL（Material Definition Language）
  - NVIDIA 的材质定义语言。USD 中将 MDL 作为一种 `Shader` 的实现类型来使用。
  - 一个 MDL Shader 常见标识：`info:id = "mdlMaterial"`（或其它 MDL 方言 token），并有 `info:mdl:*` 元数据（如 `info:mdl:sourceAsset` 指向 `.mdl`）。
- Attribute 与 AssetPath
  - USD 属性的“文件路径”值通常是 `Sdf.AssetPath` 类型（包含逻辑路径 `path` 与已解析路径 `resolvedPath`）。
  - 关键点：AssetPath 的相对路径是“相对它被作者写入的 Layer 所在目录”来解析的（称为锚点/anchor）。

> 小结：我们要做的“导出”是把一个已有的 `Material` + 其 MDL Shader 的关键信息，复制到一个“新 Stage（新文件）”里。复制过程中要小心处理“路径的基准”（否则贴图或 `.mdl` 文件会找不到）。

---

## 2. 我们想实现的函数：_export_mdl_material

函数目标：在新 Stage 里，创建一个新的 `Material`，并在其下面创建一个 `mdlShader` 节点，
- 复制原始 MDL Shader 的 `info:id`、`info:mdl:*` 等元数据
- 复制所有 `inputs:*`（对 AssetPath 类型要改写成“相对于新文件”的路径或绝对路径）
- 正确创建 `outputs:surface` 并把 `Material.outputs:surface:mdl` 连接过去

函数签名（概念化）：

```python
_export_mdl_material(new_stage, new_mat, mdl_shader_src, assets_path_mode="relative")
```
- `new_stage`：我们要写入的新 Stage
- `new_mat`：新 Stage 中的 `UsdShade.Material`（目标材质）
- `mdl_shader_src`：源 Stage 中的 MDL `UsdShade.Shader`
- `assets_path_mode`：处理文件路径的策略，"relative"（默认）或 "absolute"

---

## 3. 第一步：在新材质下创建 mdLShader 节点

```python
parent = new_mat.GetPath().pathString
shader_path = f"{parent}/mdlShader"
mdl_new = UsdShade.Shader.Define(new_stage, shader_path)
```
- 通过 `UsdShade.Shader.Define` 在新 Stage 的 `new_mat` 下面创建一个 `Shader`，命名 `mdlShader`。
- 它将作为新材质最终输出（`outputs:surface:mdl`）的来源。

---

## 4. 复制 info:id（MDL 类型标识）

```python
src_prim = mdl_shader_src.GetPrim()
id_attr = src_prim.GetAttribute("info:id")
if id_attr and id_attr.HasAuthoredValue():
    mdl_new.CreateIdAttr(id_attr.Get())
else:
    mdl_new.CreateIdAttr("mdlMaterial")
```
- `info:id` 告诉 USD 这是一个什么类型的 Shader。对 MDL 来说，常见默认值是 `mdlMaterial`。
- 我们尽量保留源节点写过的 `info:id`，否则就写入一个合理的默认值。

---

## 5. 复制 info:mdl:* 与实现提示（并改写 AssetPath）

核心逻辑：
1) 遍历源 Shader Prim 上的所有属性名；
2) 只挑与实现相关的那几类：`info:mdl:*`、`info:implementationSource`、`info:sourceAsset`；
3) 逐一复制它们的值；如果值是 `Sdf.AssetPath`，要做“路径重定位”：
   - 找出该属性“在谁的 Layer 里被写入”（锚点目录）
   - 解析出绝对路径
   - 决定写入新文件时，是改成“绝对路径”，还是改为“相对于新文件目录的相对路径”

关键代码要点（伪代码化）：

```python
new_dir = dirname(new_stage.GetRootLayer().realPath or new_stage.GetRootLayer().identifier)
for name in src_prim.GetPropertyNames():
    if name.startswith("info:mdl:") or name in ("info:implementationSource", "info:sourceAsset"):
        a_src = src_prim.GetAttribute(name)
        if a_src.HasAuthoredValue():
            v = a_src.Get()
            if isinstance(v, Sdf.AssetPath):
                anchor_dir = _anchor_dir_for_attr(a_src)  # 该属性的作者层目录
                abs_path = _resolve_abs_path(anchor_dir, v.resolvedPath or v.path)
                if abs_path:
                    if assets_path_mode == "absolute":
                        v = Sdf.AssetPath(abs_path)
                    else:  # relative
                        rel = relpath(abs_path, new_dir).replace("\\", "/")
                        v = Sdf.AssetPath(rel)
            a_dst = mdl_new.GetPrim().CreateAttribute(name, a_src.GetTypeName())
            a_dst.Set(v)
```

为什么要这么麻烦？
- 旧文件里写的是“相对旧文件”的路径；把它复制到“新文件”里，如果不改写，相对路径就会指错地方。
- 因此要先找到“原作者层”的目录（anchor），还原出绝对路径，再相对“新文件目录”去重写一次。

辅助函数说明：
- `_anchor_dir_for_attr(attr)`：根据属性的 PropertyStack 找到它的作者层（取其 `.layer.realPath` 或 `.identifier`），并返回该文件所在目录。
- `_resolve_abs_path(anchor_dir, path)`：把 `path` 解析为绝对路径；若 `path` 原本是相对路径，则以 `anchor_dir` 为基准拼接并规范化。

---

## 6. 创建 outputs:surface（MDL 输出口）

```python
mdl_new.CreateOutput("surface", Sdf.ValueTypeNames.Token)
```
- 按 MDL Shader 约定，新 Shader 需要有一个名为 `surface` 的输出口，类型通常是 `token`。

---

## 7. 复制 inputs:*（含贴图路径改写）

```python
new_dir = dirname(new_stage.GetRootLayer().realPath or new_stage.GetRootLayer().identifier)
mdl_sa_attr = src_prim.GetAttribute("info:mdl:sourceAsset")
mdl_anchor_dir = _anchor_dir_for_attr(mdl_sa_attr) if mdl_sa_attr else None
for inp in mdl_shader_src.GetInputs():
    i_dst = mdl_new.CreateInput(inp.GetBaseName(), inp.GetTypeName())
    val = inp.Get()
    if isinstance(val, Sdf.AssetPath):
        # 对贴图等 AssetPath 值做与上面相同的“重定位”
        attr = src_prim.GetAttribute(f"inputs:{inp.GetBaseName()}")
        anchor_dir = _anchor_dir_for_attr(attr) or mdl_anchor_dir
        abs_path = _resolve_abs_path(anchor_dir, val.resolvedPath or val.path)
        if abs_path:
            if assets_path_mode == "absolute":
                i_dst.Set(Sdf.AssetPath(abs_path))
            else:
                rel = relpath(abs_path, new_dir).replace("\\", "/")
                i_dst.Set(Sdf.AssetPath(rel))
        else:
            i_dst.Set(val)
    else:
        if val is not None:
            i_dst.Set(val)
```

- 处理顺序与 `info:mdl:*` 类似，但这里是 Shader 的参数输入（如颜色、贴图路径等）。
- 锚点优先级：先尝试该输入属性自身的作者层，其次回退到 `info:mdl:sourceAsset` 的作者层。
- 我们不深拷贝连接的子图，仅复制“值”（更安全且最小可用）。

---

## 8. 把新 Shader 接到新 Material 的 outputs:surface:mdl

```python
out_mdl = new_mat.GetSurfaceOutput("mdl") or new_mat.CreateSurfaceOutput("mdl")
out_mdl.ConnectToSource(mdl_new.GetOutput("surface"))
```
- 这一步完成材质输出端口与 MDL Shader 输出的连线。

---

## 9. 实用脚本与演练

我们提供了 `examples/export_mdl_material.py`：
- 读入源 USD 文件与一个 Material prim 路径
- 自动查找该 Material 连接的 MDL Shader（或可通过参数指定）
- 在指定输出路径创建一个“只包含该 Material 的新 .usda”文件，完成上面的复制与改写

运行（PowerShell）：
```powershell
# 基本用法：从源文件拷贝一个材质到新文件
python .\docs\08-exporting-mdl-material\examples\export_mdl_material.py --in .\path\to\shot.usda --mat /World/Looks/MyMat --out .\export\MyMat.usda

# 使用绝对路径写入贴图/mdl 资源
python .\docs\08-exporting-mdl-material\examples\export_mdl_material.py --in .\path\to\shot.usda --mat /World/Looks/MyMat --out .\export\MyMat.usda --assets-path-mode absolute
```

依赖：需要 USD Python 绑定（`pxr`）。

---

## 10. 易错点与排查建议
- 资源路径丢失：多数是因为没有正确“以作者层为锚点”解析旧路径，或未按新文件位置改写相对路径。
- 找不到 MDL Shader：检查 `Material.outputs:surface:mdl` 是否有连接；或手动指定 `--shader` 路径。
- 写入失败：确保输出目录存在、文件可写；Windows 下相对路径分隔符统一为 `/`。
- 大型网络：本示例只复制“值”，若你的材质是复杂子图连接网络，请另行实现深拷贝逻辑。

---

## 11. 小结（Key Takeaways）
- MDL 在 USD 中作为一种 `UsdShade.Shader` 使用，核心标识在 `info:id` 与 `info:mdl:*`。
- 跨文件复制时，务必以“作者层目录”为锚点将 `Sdf.AssetPath` 解析为绝对路径，再按新文件位置改写。
- 最小可用的导出 = 复制必要元数据 + 复制 `inputs:*` 的值 + 正确连接 `outputs:surface`。

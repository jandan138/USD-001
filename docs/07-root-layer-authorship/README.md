# Module 7: Root Layer Authorship（根层作者性）

面向完全新手，帮你弄清：Stage / Layer / Prim / PrimSpec / PrimStack 到底是什么，以及如何判断“某个 Prim 在当前根层（Root Layer）是否有作者条目”。

---

## 1. 先把几个关键词讲清楚

- Stage：可以理解为“场景视图（最终合成的结果）”。我们用 `Usd.Stage.Open('xxx.usd')` 打开一个 Stage。
- Layer：USD 文件的“图层”，比如 `a.usda`、`b.usdc`。一个 Stage 会有一个“根层”（Root Layer），还可以通过 subLayer/references/payloads 等把其他 Layer 组合进来。
- Prim：场景里的节点（类似一个物体/组件），有路径（如 `/World/Car/Wheel_FL`）。
- PrimSpec：Prim 在某个 Layer 中的“作者条目”（一个规格/定义片段）。多个 Layer 可以分别对同一个 Prim 写入不同部分信息，最终在 Stage 中被“合成”。
- PrimStack：把一个 Prim 来自各个 Layer 的 PrimSpec 堆叠起来的集合（按强度顺序）。Stage 展示的是这个“堆栈合成”的结果。

一个形象的比喻：
- Stage = 最终成品图
- Layer = 一张张半透明图层
- Prim = 图里的一个对象
- PrimSpec = 该对象在某一张图层上的“画的一笔”
- PrimStack = 针对这个对象，所有图层的“画的一笔”的叠加顺序

---

## 2. 根层（Root Layer）与“作者性”（Authorship）

- 根层就是 `stage.GetRootLayer()` 指向的那个 Layer（也就是你打开的主文件或者你指定为根的文件）。
- 我们有时只想导出“仅在根层中亲自写过（有作者条目）”的东西；而来自外部文件（通过 subLayer、reference、payload 引入）的东西先不导出。这就需要判断某个 Prim 在根层有没有 PrimSpec。

为什么要这样做？
- 场景里很多东西可能是“引用进来的资产”（例如把一个汽车资产 `.usd` 引用到你的镜头场景里）。你可能只想导出自己在当前文件中真正编辑/定义的材质，而忽略外部资产里自带的材质。这时就会有一个选项类似 `include_external=False`：只导出根层作者所定义的内容。

---

## 3. 判断逻辑（Python 实现）

核心函数思路：
- 取根层的 `identifier`。
- 遍历目标 Prim 的 `PrimStack`（即这个 Prim 在所有 Layer 上的 PrimSpec）。
- 只要出现一条 `spec.layer.identifier == root_id`，就说明“根层写过它”。

示例实现：

```python
from pxr import Usd

def _is_in_root_layer(stage: Usd.Stage, prim: Usd.Prim) -> bool:
    """判断 prim 是否在当前 Stage 的 Root Layer 中有作者条目（PrimSpec）。"""
    root_id = stage.GetRootLayer().identifier
    try:
        for spec in prim.GetPrimStack():
            if spec.layer.identifier == root_id:
                return True
    except Exception:
        # 某些无效 prim 或无法获取 stack 的情况，这里保守返回 False
        pass
    return False
```

使用方式：

```python
stage = Usd.Stage.Open('shot.usda')
prim = stage.GetPrimAtPath('/World/Looks/MyMaterial')
if _is_in_root_layer(stage, prim):
    print('这个 Prim 在根层有作者条目（是我们在当前文件里写过的）')
else:
    print('这个 Prim 不是由根层直接定义（可能来自外部引用）')
```

---

## 4. 结合导出过滤的典型场景

当我们导出材质时，可能有一个选项：`include_external=False`，表示：
- 只导出“根层作者”的材质
- 忽略来自外部引用文件（assets）的材质

伪代码：

```python
materials = []
for prim in stage.Traverse():
    if prim.GetTypeName() == 'Material':  # 或使用 UsdShade.Material 判定
        if include_external:
            materials.append(prim)
        else:
            if _is_in_root_layer(stage, prim):
                materials.append(prim)
```

---

## 5. 边界与注意事项（给新手的贴士）

- 无效 Prim：`stage.GetPrimAtPath` 可能返回无效 Prim（路径错/不存在）。先用 `prim.IsValid()` 判断。
- 只读 vs 编辑：判断作者性不代表你正在改动 Stage；读取 `PrimStack` 只是在看合成信息。
- 性能：对海量 Prim 逐个看 `PrimStack` 可能有开销。可先用遍历谓词（如 `Usd.PrimIsDefined`）减少数量。
- Layer 标识：这里用 `layer.identifier` 来对比是否是 Root Layer。
- 组合来源：即使 Prim 在根层“存在作者条目”，它也可能同时从其它 Layer 继承/覆盖到更多属性——这很正常，USD 的合成本来就是“多图层叠加”。

---

## 6. 动手跑一跑（示例脚本）

我们在 `examples/is_in_root_layer.py` 中提供了一个可执行脚本：
- 打开指定 USD 文件
- 可选从某个 prim 路径开始
- 列出在根层有作者条目的 prim（可按类型过滤，比如 Material）

运行（PowerShell）：

```powershell
python .\docs\07-root-layer-authorship\examples\is_in_root_layer.py --file .\path\to\shot.usda

# 只看 Material，并从指定路径起步
python .\docs\07-root-layer-authorship\examples\is_in_root_layer.py --file .\path\to\shot.usda --root /World/Looks --type Material
```

依赖：需要 USD 的 Python 绑定（`pxr`）。Conda 可用：`conda install -c conda-forge usd`。

---

## 7. 小结（Key Takeaways）

- Stage 是合成视图；Layer 是组成它的“图层文件”。
- 一个 Prim 在多个 Layer 上可以各有一个 PrimSpec，这些 PrimSpec 构成 PrimStack。
- 判断“是否由根层作者定义”就是看 PrimStack 里是否包含来自 Root Layer 的 PrimSpec。
- 这个判断在导出、清洗场景资产时非常有用，能精准筛出“当前文件亲自编辑过”的元素。

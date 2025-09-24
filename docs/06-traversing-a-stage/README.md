# Module 6: Traversing a Stage

本章介绍如何在 OpenUSD 中遍历场景图（scenegraph），包括遍历模式、预过滤谓词（predicates）与 Python 实践示例。

## How Does It Work?

当我们在 Stage 中打开一个 Layer 后，就可以使用多种方式遍历场景图：
- 迭代子 `Prim`、访问父 `Prim`，并在层级中查找目标 `Prim`。
- 这些能力由 `Stage` 提供，它负责加载、编辑与保存 USD 数据。

遍历的底层由 `Usd.PrimRange` 驱动；许多方法（如 `stage.Traverse()`）都是在其基础上构建的。

## Traversal Modes

`Usd.PrimRange` 支持两种常用遍历模式：
- Default：按层级向下迭代子 `Prim`（每个 `Prim` 访问一次）。
- PreAndPostVisit：深度优先遍历，对每个 `Prim` 访问两次：
  - 预访问（pre-visit）：第一次遇到该 `Prim` 时；
  - 后访问（post-visit）：从其子层级“返回”时。

## Predicates（谓词预过滤）

可以通过谓词对遍历结果做预过滤（逻辑与 `&`、或 `|`、取反 `~` 可组合）：
- `Usd.PrimIsActive` → `Usd.Prim.IsActive()`：`active` 元数据为 `True`
- `Usd.PrimIsLoaded` → `Usd.Prim.IsLoaded()`：其（祖先）payload 已加载
- `Usd.PrimIsModel` → `Usd.Prim.IsModel()`：`kind` 为 `Kind.Tokens.model` 的子类
- `Usd.PrimIsGroup` → `Usd.Prim.IsGroup()`：`kind` 为 `Kind.Tokens.group`
- `Usd.PrimIsAbstract` → `Usd.Prim.IsAbstract()`：`specifier == Sdf.SpecifierClass`
- `Usd.PrimIsDefined` → `Usd.Prim.IsDefined()`：`specifier == Sdf.SpecifierDef`

## Working With Python

```python
from pxr import Usd

# 打开 USD 文件并创建 Stage
stage = Usd.Stage.Open('car.usda')

# 1) 默认遍历（所有 prim，默认谓词）
for prim in stage.Traverse():
    print(prim.GetPath())

# 2) 定义谓词：仅遍历 active 且 payload 已加载的 prim
predicate = Usd.PrimIsActive & Usd.PrimIsLoaded
for prim in stage.Traverse(predicate=predicate):
    print(prim.GetPath())

# 3) 从特定 prim 开始遍历（带谓词）
prim = stage.GetPrimAtPath('/World/Car')
for p in Usd.PrimRange(prim, predicate=predicate):
    print(p.GetPath())
```

Pre-and-post 访问示例（可观察进入/退出子层级的时机）：

```python
from pxr import Usd

stage = Usd.Stage.Open('car.usda')
root = stage.GetPseudoRoot()  # 或者指定某个 prim 作为根

# 使用 PreAndPostVisit 获取可区分 pre/post 的迭代器
rng = Usd.PrimRange.PreAndPostVisit(root, predicate=Usd.PrimIsDefined)
it = iter(rng)
while True:
    try:
        prim = next(it)
    except StopIteration:
        break
    phase = 'post' if it.IsPostVisit() else 'pre'
    print(f'[{phase}]', prim.GetPath())
```

## 示例脚本

我们提供了一个实用的示例脚本：`examples/traverse_demo.py`，支持以下能力：
- 打开一个 `.usd/.usda/.usdc` 文件并遍历
- 从指定 `--root` prim 路径开始
- 使用 `--active-loaded-only` 启用 `active & loaded` 谓词
- 使用 `--prepost` 切换为 PreAndPostVisit 模式

运行方式（需先安装 USD Python 绑定）：

```powershell
python .\docs\06-traversing-a-stage\examples\traverse_demo.py --file .\path\to\car.usda

# 指定 root、启用谓词并使用 pre/post 访问
python .\docs\06-traversing-a-stage\examples\traverse_demo.py --file .\path\to\car.usda --root /World/Car --active-loaded-only --prepost
```

环境准备（任选其一）：
- 使用 Conda 安装：`conda install -c conda-forge usd`
- 或使用官方二进制发布（设置 `PYTHONPATH` 指向 `pxr` 绑定目录）

## Key Takeaways

- Stage 遍历是查询与操作场景图的基础能力。
- 使用谓词进行预过滤可提升效率与准确性。
- `PreAndPostVisit` 能显式区分进入/退出某个子层级的时机，便于编写递归/栈式逻辑。

## Tips & Pitfalls

- 大场景遍历前先用谓词过滤（如 `IsActive`、`IsLoaded`、`IsDefined`）。
- 在按路径起始遍历前先检查 `prim.IsValid()`，避免无效路径。
- 如需只读访问，尽量避免不必要的 `Stage` 编辑操作以减少开销。

---

更多示例建议放到 `examples/`，并在此处附上简要说明与运行命令。

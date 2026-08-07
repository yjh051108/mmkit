# FIGURE_QUICK_REF

> 本文件为图表生成快速决策表。auto-extracted from figure_style_guide.md，保持精简。

## 图表类型决策树

| 数据特征 | 推荐图表 | 代码入口 |
|---------|---------|---------|
| 双变量关系 | 散点图 / 回归图 | `plot_utils.scatter_fit()` |
| 单变量分布 | 直方图 / KDE | `plot_utils.hist_kde()` |
| 多类别对比 | 柱状图 / 箱线图 | `plot_utils.bar_compare()` |
| 时间序列 | 折线图 + 置信区间 | `plot_utils.line_ci()` |
| 多维数据 | 热力图 | `plot_utils.heatmap()` |
| 层级关系 | 树状图 / 旭日图 | `plot_utils.dendrogram()` |
| 地理数据 | 分级统计地图 | `plot_utils.choropleth()` |
| 网络关系 | 网络图 | `plot_utils.network()` |
| 流程图 / 架构图 | draw.io | 手绘或 `drawio_check.py` 验证 |

## 配色规则（快速参考）

```python
from _utils.plot_utils import PALETTE, setup_style

setup_style()  # 必须在绘图前调用

# PALETTE 是预定义色板，never hardcode hex
# 主色: PALETTE["primary"]
# 辅色: PALETTE["secondary"]
# 强调色: PALETTE["accent"]
# 序列色: PALETTE["sequential"]
# 分类色: PALETTE["categorical"]
```

## 保存规则

```python
from _utils.plot_utils import save_fig

save_fig(fig, "figures/fig_xxx.pdf")  # 矢量优先 PDF
save_fig(fig, "figures/fig_xxx.png", dpi=300)  # 位图用 PNG 300dpi
```

## 反模式（禁止）

- ❌ hardcode hex 颜色（如 `color="#1f77b4"`）
- ❌ 用 matplotlib 默认样式（必须先 `setup_style()`）
- ❌ 保存为 JPG（有损压缩）
- ❌ 图表无标题、无轴标签、无单位
- ❌ 矢量图和位图不同时提供（关键图必须 PDF + PNG 双输出）

## 自检

每张图画完后必须跑：
```bash
python _utils/figure_check.py figures/fig_xxx.pdf
```

## 详细参考

- 配色规则详见 `_utils/figure_style_guide.md`
- 代码模板详见 `_utils/figure_recipes_*.md`
- 示例图详见 `_utils/figure_exemplars.md`

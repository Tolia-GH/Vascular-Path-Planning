# 血管路径规划 3D 演示前端 —— 开发计划

> 版本: v2.0  
> 状态: 未开展硬件联调联试，仅路径规划3D演示  
> 技术路线: **方案 C — Python + PyVista + Qt**  
> 基于文档: INDEX.md（血管介入导航系统技术设计文档 0422）

---

## 1. 范围与边界

### 1.1 包含范围

| 模块 | 说明 |
|------|------|
| 血管3D模型渲染 | 基于现有 VTK 血管模型 + 中心线数据 |
| 中心线骨架显示 | 线段/管线渲染，分支拓扑可视化 |
| 路径规划引擎 | A* 全局规划，基于中心线重采样图 |
| 规划路径可视化 | 路径高亮、起终点标记、路径段颜色编码 |
| 交互选点 | 3D 点拾取设定起点/终点，触发路径规划 |
| 路径信息面板 | 路径长度、节点数、曲率峰值、可行性等级 |
| 分支高亮/段选择 | 左侧线段列表 + 选中高亮（已有 Qt 版基础） |
| 代价权重调节 | 前端滑块调节 w_len / w_curv / w_rad 等权重 |

### 1.2 不包含范围

| 排除项 | 原因 |
|--------|------|
| DSA/X-ray 2D 视图 | 需影像流 + 配准，非演示范围 |
| 术中实时导航 UI | 需硬件 + ROS2 + 状态估计 |
| 配准(2D/3D Registration) | 需术中影像 + 跟踪器 |
| 安全监督/碰撞检测 | 需实时位姿 + 力反馈 |
| ROS2 / DDS 通信 | 硬件未联调 |
| VLA / LLM 模块 | 高层AI辅助，非演示核心 |
| 瑞鈊跟踪设备对接 | 硬件未接入 |
| WebSocket 实时推送 | 无后端/硬件数据源 |
| 导丝/导管运动学仿真 | SOFA/Cosserat Rod 属仿真层 |

---

## 2. 技术选型

### 2.1 方案对比

| 方案 | 渲染库 | 语言 | 优势 | 劣势 |
|------|--------|------|------|------|
| **A: React + vtk.js** | vtk.js | TypeScript/JS | 与 INDEX.md 技术栈一致；医学影像社区标准；支持 Volume Rendering | 学习曲线陡；Bundle 体积大；A* 需移植 |
| **B: React + Three.js** | Three.js | TypeScript/JS | 生态丰富；浏览器部署；性能好 | VTK→glTF 转换链路脆弱；A* 需移植 |
| **C: Python (PyVista + Qt)** | PyVista/VTK + Qt | Python | **已有代码直接复用**；VTK 原生加载无需格式转换；开发速度最快 | 非 Web 前端；需 Python 运行环境 |

### 2.2 推荐方案（最终选择）

**最终选择：方案 C — Python + PyVista + Qt**

选择理由：

1. **最大化代码复用**：现有 Python A* 算法（`a_star.py`）、VTK 加载（`pyvista.read()`）、中心线分割（`split_polydata_lines`）、线段列表（`CenterlineViewer`）全部直接复用，零移植成本
2. **零数据转换**：VTK 文件是 PyVista 原生格式，无需 vtk→gltf 预转换链路
3. **医学影像生态**：PyVista 底层是 VTK，与 3D Slicer/VMTK 技术栈天然一致
4. **验证速度最快**：在 Python 环境中可随时调用现有脚本进行算法调参、数据验证
5. **当前阶段匹配**：未开展硬件联调阶段的核心需求是快速验证路径规划算法与 3D 可视化交互，桌面应用最合适

**后续演进**：在 Phase 5（硬件联调阶段），如需 Web 部署，再按 INDEX.md 技术栈移植到 React + vtk.js/Three.js。届时路径规划核心算法已充分验证，移植仅涉及渲染层。

### 2.3 硬件联调阶段选型分析

当进入瑞鈊设备联调阶段时，系统数据流如 INDEX.md 第 3 章定义：

```
瑞鈊SDK (C++ Windows)
  → hardware_interface_node (ROS2 C++ 节点)
    → state_estimator_node (ROS2 C++ 节点)
      → ROS2 Bridge (Python FastAPI 后端)
        → WebSocket (10~30 Hz 位姿)
          → 前端 Web UI
```

**前端从不直接接触瑞鈊SDK**。前端仅消费 WebSocket JSON 消息，因此三种方案对硬件联调适配性如下：

| 维度 | 方案 A (vtk.js) | 方案 B (Three.js) | 方案 C (PyVista) |
|------|:--:|:--:|:--:|
| WebSocket 接入 | ✅ 浏览器原生API | ✅ 浏览器原生API | △ 需自建 Qt/Flask 桥 |
| 实时场景更新 | △ VTK管线偏重 | ✅ r3f响应式更新轻量 | ✘ VTK重建开销大 |
| 动态对象管理 (器械标记/预测轨迹) | △ | ✅ 性能最优 | ✘ 不适合高频更新 |
| DICOM/Volume Rendering | ✅ 原生支持 | ❌ 需混用Cornerstone3D | ✅ VTK原生支持 |
| 与 INDEX.md 一致 | ✅ 文档指定栈 | ⚠️ 但文档4.2节同时列出Three.js | ✘ 非Web前端 |
| 部署 | ✅ 静态文件 | ✅ 静态文件 | ✘ Python环境依赖 |
| Bundle 体积 | ~2MB+ gzipped | ~500KB gzipped | N/A |
| 适合场景 | 需Volume Rendering时 | 纯表面+动态场景 | 算法调参/离线验证 |

**结论**：硬件联调阶段**推荐继续使用方案 B (Three.js)**。原因：

1. Three.js 对实时动态场景（30Hz器械位姿、预测轨迹、安全走廊变化）的响应式更新性能优于 vtk.js
2. INDEX.md 4.2 节同时列出 `Cornerstone3D` 与 `Three.js` 作为系统组件——混用在设计允许范围内
3. 当前演示阶段的核心渲染对象为表面模型 + 线段 + 标记点，Three.js 完全覆盖
4. 真正需要 vtk.js/Cornerstone3D 的时机是引入 DSA/CTA Volume Rendering，而非硬件联调本身

**后续混合方案**：当需要 Volume 叠加时，在现有 Three.js 场景旁引入 Cornerstone3D 视口，而非整体替换渲染库。

---

## 3. 数据资产盘点

### 3.1 已有数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 血管模型 | `source/vtk/blood_vessels.vtk` | 3D 血管表面渲染 |
| 中心线(合并) | `source/vtk/Centerline_curves_merged.vtk` | 路径规划图 + 线段渲染 |
| 中心线(原始) | `source/vtk/Centerline model.vtk` | 备选中心线 |
| 有向图 JSON | `source/graphs/centerline_vessel_net.json` | A* 搜索图（~3000+ 节点） |
| 终点集 FCSV | `source/fcsv/Endpoints.fcsv` | 预设起点/终点 |
| 分支 FCSV | `source/fcsv/intervenPoints.fcsv` | 分支交叉点 |

### 3.2 已有代码

| 模块 | 文件 | 可复用程度 |
|------|------|------------|
| A* 算法 | `vascular_path_planning/planning/a_star.py` | ★★★★★ 直接复用 |
| Node 类 | `vascular_path_planning/planning/node.py` | ★★★★★ |
| PyVista 可视化 | `path_planing/visualize.py` | ★★★★☆ 可复用核心逻辑 |
| Qt 线段选择器 | `path_planing/visualize.py: CenterlineViewer` | ★★★★☆ 交互范式可参考 |
| 图转换器 | `preprocess/converter.py` | ★★★☆☆ 理解邻接表结构 |
| B样条平滑 | `preprocess/BSplineSmoother.py` | ★★★☆☆ 路径后处理 |
| 区域生长 | `preprocess/region_growing.py` | ★★★☆☆ 启发式距离预计算 |

---

## 4. 架构设计

### 4.1 总体分层

```
┌─────────────────────────────────────────────────────┐
│                  UI Layer (PyQt5)                    │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 3D Viewer │ │  Info    │ │  Control Panel    │  │
│  │ (PyVista  │ │  Panel   │ │ (权重/起终点/模式) │  │
│  │ QtInter-  │ │ (QtWidget│ │ (QtWidgets)       │  │
│  │  actor)   │ │ s)       │ │                   │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│              App State (QObject/Signals)              │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Scene     │ │ Planner  │ │ Segment           │  │
│  │ State     │ │ State    │ │ State             │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│               Logic Layer (Python 复用)              │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ a_star.py │ │ node.py  │ │ BSplineSmoother   │  │
│  │ (已有)    │ │ (已有)   │ │ .py (已有)        │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│                  Data Layer                          │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ VTK       │ │ JSON     │ │ FCSV              │  │
│  │ (pv.read) │ │ Graph    │ │ Endpoints         │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 4.2 数据流

```
VTK血管模型 (pv.read) → PyVista Mesh → 3D Scene (半透明表面)
VTK中心线  (pv.read) → split_polydata_lines → 分段渲染 + SegmentList
JSON图 → converter.py加载 → Adjacency Map → A* Planner (已有)
                    ↓
              中心线点云 → KDTree → 3D点选映射 → 起终点
                    ↓
            A* 搜索结果 → 路径节点序列 → build_polyline_from_points → 路径管线渲染
                    ↓
            Path Info Calculator → 路径统计 → Info Panel
```

### 4.3 复用现有代码对照

| 现有文件 | 复用方式 | 对应功能 |
|----------|----------|----------|
| `path_planing/visualize.py: visualize_centerline_qt()` | 直接扩展 | 整体应用框架（Qt分割窗口+线段列表+3D视图） |
| `path_planing/visualize.py: split_polydata_lines()` | 直接复用 | 中心线分段 |
| `path_planing/visualize.py: build_polyline_from_points()` | 直接复用 | 路径折线构建 |
| `path_planing/visualize.py: build_splitted_centerline()` | 直接复用 | 构建分段中心线 PolyData |
| `path_planing/visualize.py: visualize_vessels()` | 参考 | 血管模型加载与渲染 |
| `vascular_path_planning/planning/a_star.py` | 直接复用 | A* 路径规划 |
| `vascular_path_planning/planning/node.py` | 直接复用 | 节点数据结构 |
| `path_planing/a_star.py` | 直接复用 | A* 备选实现 + 图构建 |
| `preprocess/BSplineSmoother.py` | 直接复用 | 路径平滑 |
| `preprocess/converter.py` | 参考 | JSON 图加载逻辑 |

---

## 5. 功能清单

### Phase 1: 核心渲染 + 路径规划 (MVP) — 1周

| ID | 功能 | 优先级 | 预计工时 | 说明 |
|----|------|--------|----------|------|
| F1 | 血管模型 3D 渲染 (半透明表面) | P0 | 1h | **已有** `visualize_vessels()`，仅需集成 |
| F2 | 中心线骨架渲染 (管线/分段) | P0 | 1h | **已有** `visualize_centerline_qt()` 核心逻辑 |
| F3 | 3D 场景基础交互 (旋转/缩放/平移) | P0 | 0.5h | PyVista 内建交互，零开发 |
| F4 | 线段列表 + 点击高亮 | P0 | 0.5h | **已有** `CenterlineViewer` 完整实现 |
| F5 | JSON 图加载 + 邻接表构建 | P0 | 2h | **已有** `a_star.py` 图构建逻辑，需适配 |
| F6 | A* 路径规划 (基于真实血管图) | P0 | 1h | **直接复用** `vascular_path_planning/planning/a_star.py` |
| F7 | 规划路径 3D 高亮显示 | P0 | 1h | **已有** `visualization_pyvista()` 路径渲染逻辑 |
| F8 | 起点/终点标记 (球体) | P0 | 0.5h | **已有** `visualization_pyvista()` 中 `add_points` |
| F9 | 3D 点拾取设定起点/终点 | P0 | 2h | **已有** `enable_point_picking` 回调范式 |
| F10 | 路径统计面板 (长度/节点数/曲率/可行性) | P1 | 3h | 新增 QtWidget |
| F11 | 预设端点加载 (基于 FCSV) | P1 | 2h | 解析 `Endpoints.fcsv` → 下拉选择 |

### Phase 2: 交互 + 可视化增强 — 1周

| ID | 功能 | 优先级 | 预计工时 | 说明 |
|----|------|--------|----------|------|
| F12 | 分支拓扑可视化 (分叉点高亮) | P1 | 3h | 基于 graph JSON 中分支信息 |
| F13 | 路径可行性颜色编码 (Green/Yellow/Orange/Red) | P1 | 4h | 按曲率/半径分段着色 |
| F14 | 多候选路径对比显示 | P2 | 4h | A* 多结果 + 并行渲染 |
| F15 | 节点属性悬浮提示 (Qt Tooltip) | P2 | 3h | radius/curvature/flow_distance |
| F16 | 安全走廊可视化 (管状半透明) | P2 | 5h | TubeFilter + opacity |
| F17 | 代价权重实时调节面板 | P2 | 3h | QSlider × 5，触发重规划 |

### Phase 3: 高级功能 — 1周

| ID | 功能 | 优先级 | 预计工时 | 说明 |
|----|------|--------|----------|------|
| F18 | 路径平滑后处理 (B-spline) | P2 | 2h | **直接复用** `preprocess/BSplineSmoother.py` |
| F19 | 曲率热力图 (路径着色) | P2 | 3h | scalars 映射 + colorbar |
| F20 | 路径剖面图 (半径/曲率曲线) | P3 | 4h | matplotlib 嵌入 Qt |
| F21 | 导出路径数据 (JSON/CSV) | P3 | 2h | Python 原生序列化 |
| F22 | 场景状态保存/加载 | P3 | 3h | JSON 序列化场景参数 |
| F23 | 手动选段导航 (线段级路径拼接) | P3 | 4h | 多段点选 → 跨段 A* 连接 |

---

## 6. 项目目录结构

```
path_planing/                         # 主开发目录（扩展现有）
├── main_qt.py                        # 【新建】主入口，Qt 应用
├── visualize.py                      # 【扩展现有】可视化模块（已含核心函数）
├── a_star.py                         # 【已有】A* 规划 + 图构建
├── node.py                           # 【已有】节点数据结构
│
├── ui/                               # 【新建】UI 模块
│   ├── __init__.py
│   ├── main_window.py                # 主窗口（继承 QMainWindow）
│   ├── viewer_3d.py                  # 3D 视图组件（封装 PyVista QtInteractor）
│   ├── control_panel.py              # 控制面板（起终点选择 / 权重调节）
│   ├── path_info_panel.py            # 路径信息面板
│   ├── segment_list_panel.py         # 线段列表面板（扩展已有 CenterlineViewer）
│   └── status_bar.py                 # 底部状态栏
│
├── engine/                           # 【新建/重组】规划引擎
│   ├── __init__.py
│   ├── planner.py                    # 规划器统一接口（封装已有 a_star）
│   ├── graph_loader.py               # JSON 图加载器（提取自 converter.py）
│   └── path_analyzer.py              # 路径分析（长度/曲率/半径/可行性）
│
├── render/                           # 【新建】渲染辅助
│   ├── __init__.py
│   ├── vessel_renderer.py            # 血管模型渲染（封装 visualize_vessels 逻辑）
│   ├── centerline_renderer.py        # 中心线渲染（封装 build_splitted_centerline）
│   ├── path_renderer.py              # 路径渲染（颜色编码/管线/标记）
│   └── color_map.py                  # 可行性颜色映射
│
└── utils/                            # 【新建】工具
    ├── __init__.py
    ├── kd_tree.py                    # KDTree（从已有代码提取）
    └── data_export.py                # 路径数据导出

vascular_path_planning/               # 【已有】规划算法（不作修改）
└── planning/
    ├── a_star.py                     # A* 算法核心
    └── node.py                       # 节点类

preprocess/                           # 【已有】预处理工具（不作修改）
├── BSplineSmoother.py                # B样条平滑
├── converter.py                      # 图转换
└── region_growing.py                 # 区域生长

source/                               # 【已有】数据资产（不作修改）
├── vtk/                              # VTK 血管模型 + 中心线
├── graphs/                           # JSON 有向图
├── fcsv/                             # 端点/分支 FCSV
└── mrk/                              # 标记点

requirements.txt                      # 【更新】添加 pyvista, pyvistaqt, PyQt5, numpy, scipy
PLAN_3D_DEMO.md                       # 本计划文档
```

---

## 7. 核心算法设计

### 7.1 A* 路径规划 (直接复用)

系统直接复用 `vascular_path_planning/planning/a_star.py`，无需移植。接口保持不变：

```python
# 已有接口 (vascular_path_planning/planning/a_star.py)
from vascular_path_planning.planning.a_star import AStar
from vascular_path_planning.planning.node import Node

# 规划器封装 (新建 engine/planner.py)
class PathPlanner:
    """统一规划器接口，封装已有 A* 实现"""
    def __init__(
        self,
        graph_json_path: str,      # centerline_vessel_net.json
        centerline_vtk_path: str,  # 中心线 VTK (用于属性查询)
    ):
        self.graph = self._load_graph(graph_json_path)
        self.astar = AStar(self.graph)
        self.kdtree = KDTree(self.graph.node_positions)

    def plan(
        self,
        start_xyz: Tuple[float, float, float],
        goal_xyz: Tuple[float, float, float],
        weights: CostWeights | None = None,
    ) -> PlanResult:
        """从 3D 坐标规划路径"""
        start_idx = self.kdtree.nearest(start_xyz)
        goal_idx = self.kdtree.nearest(goal_xyz)
        path_nodes = self.astar.search(start_idx, goal_idx, weights)
        return self._analyze(path_nodes)
```

### 7.2 代价权重模型 (对齐 INDEX.md)

```python
@dataclass
class CostWeights:
    w_len: float = 1.0    # 距离权重
    w_curv: float = 0.3   # 曲率惩罚
    w_rad: float = 0.2    # 半径惩罚（小半径 → 高惩罚）
    w_dir: float = 0.1    # 方向偏差惩罚
    w_risk: float = 0.0   # 风险惩罚 (demo 阶段暂为 0)

    def apply(self, edge: Edge) -> float:
        return (
            self.w_len * edge.length +
            self.w_curv * edge.curvature_penalty +
            self.w_rad * edge.radius_penalty +
            self.w_dir * edge.direction_penalty +
            self.w_risk * edge.risk_penalty
        )
```

### 7.3 KDTree 加速最近点查找

```python
# 3D 点选 → 最近中心线节点
# 用于交互式起终点设定
from scipy.spatial import KDTree

class PointIndex:
    def __init__(self, points: np.ndarray):  # shape (N, 3)
        self.tree = KDTree(points)

    def nearest(self, query: np.ndarray) -> Tuple[int, float]:
        """返回 (最近点索引, 距离_mm)"""
        dist, idx = self.tree.query(query)
        return idx, dist
```

### 7.4 路径分析器

```python
# engine/path_analyzer.py
@dataclass
class PlanResult:
    path_xyz: np.ndarray              # 路径点序列 (N, 3)
    total_length_mm: float            # 总长度
    total_cost: float                 # 总代价
    peak_curvature: float             # 峰值曲率 (1/mm)
    min_radius_mm: float              # 最小局部半径
    feasibility: str                  # 'green' | 'yellow' | 'orange' | 'red'
    node_count: int                   # 路径节点数

def analyze_path(
    path_points: np.ndarray,
    centerline_attrs: dict,  # 节点属性 (radius, curvature, ...)
) -> PlanResult:
    """分析路径并评定可行性等级"""
    ...
    # 可行性定义 (对齐 INDEX.md):
    # green  : curvature < 阈值 && radius > 阈值
    # yellow : curvature 接近边界
    # orange : radius 裕量不足
    # red    : 违反运动学约束
```

---

## 8. 可视化规范

### 8.1 颜色编码 (对齐 INDEX.md)

| 颜色 | 含义 | 适用场景 |
|------|------|----------|
| 🟢 Green `#00FF00` | 安全可行 | 低曲率、大半径路径段 |
| 🟡 Yellow `#FFFF00` | 曲率较高/接近边界 | 中等曲率段 |
| 🟠 Orange `#FF8800` | 接触风险/裕量不足 | 高曲率或狭窄段 |
| 🔴 Red `#FF0000` | 不可达/禁入 | 违反运动学约束 |

### 8.2 渲染样式 (PyVista)

| 对象 | 样式 | PyVista 实现 |
|------|------|-------------|
| 血管表面 | 半透明红色 rgba(255,0,0,0.3) | `add_mesh(vessels, color='red', opacity=0.3)` |
| 中心线 | 深灰 #333，line_width=1.5 | `add_mesh(seg, color='#333333', line_width=1.5)` |
| 规划路径 | 亮绿 #00FF00，line_width=4，管线 | `add_mesh(path_line, color='#00FF00', line_width=4)` + `render_lines_as_tubes=True` |
| 起点 | 蓝色球体 r=2mm | `add_points(start_pt, color='blue', point_size=10, render_points_as_spheres=True)` |
| 终点 | 绿色球体 r=2mm | `add_points(goal_pt, color='green', point_size=10, render_points_as_spheres=True)` |
| 分叉点 | 黄色小点 r=1mm | `add_points(bifurcation_pts, color='yellow', point_size=6, render_points_as_spheres=True)` |
| 候选路径 | 虚线样式 | `add_mesh(candidate, color='orange', line_width=2, style='wireframe')` |
| 安全走廊 | 管状半透明 | `add_mesh(tube, color='cyan', opacity=0.15)` |

### 8.3 坐标系

- 系统: **LPS** (Left-Posterior-Superior)
- 单位: **mm**
- 场景默认朝向: 相机初始位置设为俯视 LPS 坐标系最佳观察角度
- 坐标轴: `plotter.show_axes()` 或 `plotter.add_axes()`

### 8.4 背景与光照

- 背景色: 白色 `plotter.background_color = 'white'`
- 光照: PyVista 默认三点光源（可调整强度）
- 网格: `plotter.show_grid()` 显示 LPS 坐标参考面

---

## 9. UI 布局设计

### 9.1 总体布局 (PyQt5 QMainWindow)

```
┌──────────────────────────────────────────────────────────┐
│ Menu Bar: File | View | Help                              │
├──────────────────────────────────────────────────────────┤
│ Top Info Bar (QFrame): 标题 | 数据节点/边数 | 模式指示器    │
├─────────────────────────────┬────────────────────────────┤
│                              │  Path Info Panel          │
│   3D Viewer                  │  (QGroupBox)              │
│   (PyVista QtInteractor)     │  ┌──────────────────────┐ │
│                              │  │ 路径长度:  xxx.xx mm │ │
│  🟢 Vessel Model (半透明)    │  │ 节点数:    xxx       │ │
│  ⚫ Centerlines (管线)       │  │ 曲率峰值:  x.xxx /mm │ │
│  🟢 Planned Path (绿色粗线)  │  │ 最小半径:  xxx.xx mm │ │
│  🔵 Start Marker (蓝球)      │  │ 可行性:    🟡 Yellow │ │
│  🟢 Goal Marker (绿球)       │  └──────────────────────┘ │
│  🟡 Bifurcation Points       │                            │
│                              │  Control Panel            │
│                              │  (QGroupBox)              │
│                              │  ┌──────────────────────┐ │
│                              │  │ 起点: [FCSV下拉▼][+3D]│ │
│                              │  │ 终点: [FCSV下拉▼][+3D]│ │
│                              │  │ w_len:  ──●──  1.0   │ │
│                              │  │ w_curv: ──●──  0.3   │ │
│                              │  │ w_rad:  ──●──  0.2   │ │
│                              │  │ w_dir:  ──●──  0.1   │ │
│                              │  │ [ 规划路径 ] [ 清除 ] │ │
│                              │  └──────────────────────┘ │
│                              │                            │
│                              │  Segment List             │
│                              │  (QGroupBox)              │
│                              │  ┌──────────────────────┐ │
│                              │  │ 无高亮                │ │
│                              │  │ segment_0 (42 pts)   │ │
│                              │  │ segment_1 (38 pts)   │ │
│                              │  │ segment_2 (55 pts)   │ │
│                              │  │ ...                   │ │
│                              │  └──────────────────────┘ │
├─────────────────────────────┴────────────────────────────┤
│ Bottom Status Bar (QStatusBar):                             │
│ 坐标: (xxx, xxx, xxx) | 帧率: 30 FPS | 选中: node_142     │
│ 图节点数: 3124 | 边数: 6038 | 数据: blood_vessels.vtk      │
└──────────────────────────────────────────────────────────┘
```

### 9.2 组件树 (PyQt5 Widget 层级)

```
QMainWindow (MainWindow)
├── QMenuBar
│   ├── File → Load Data | Export Path | Exit
│   ├── View → Reset Camera | Top View | Front View | Side View
│   └── Help → About
├── QToolBar / TopInfoBar (QFrame)
│   ├── QLabel (标题 "血管路径规划 3D 演示")
│   ├── QLabel (数据信息: 节点数/边数)
│   └── QLabel (模式: 路径规划)
├── QSplitter (水平分割 70/30)
│   ├── Viewer3D (PyVista QtInteractor) — 左侧 70%
│   │   ├── VesselMesh      (actor) — 血管半透明表面
│   │   ├── CenterlineSegs  (actor[]) — 分段中心线
│   │   ├── PathOverlay     (actor) — 规划路径管线
│   │   ├── StartMarker     (actor) — 起点球
│   │   ├── GoalMarker      (actor) — 终点球
│   │   └── BifurcationPts  (actor) — 分叉点标记
│   └── RightPanel (QWidget → QVBoxLayout) — 右侧 30%
│       ├── PathInfoPanel (QGroupBox)
│       │   ├── LengthLabel (QLabel)
│       │   ├── NodesLabel (QLabel)
│       │   ├── CurvatureLabel (QLabel)
│       │   ├── RadiusLabel (QLabel)
│       │   └── FeasibilityLabel (QLabel, 颜色背景)
│       ├── ControlPanel (QGroupBox)
│       │   ├── StartCombo (QComboBox) + PickStartBtn (QPushButton)
│       │   ├── GoalCombo (QComboBox) + PickGoalBtn (QPushButton)
│       │   ├── WeightSliders (QSlider[] × 4)
│       │   ├── PlanBtn (QPushButton "规划路径")
│       │   └── ClearBtn (QPushButton "清除")
│       └── SegmentListPanel (QGroupBox)
│           └── SegmentList (QListWidget)
└── QStatusBar
    ├── CoordLabel (QLabel, 永久)
    ├── FpsLabel (QLabel, 永久)
    └── SelectionLabel (QLabel, 永久)
```

### 9.3 信号/槽连接 (核心交互)

```python
# 3D 点选 → 更新起点/终点
viewer_3d.point_picked.connect(control_panel.on_point_picked)

# FCSV 下拉选择 → 更新起/终点 → 触发规划
control_panel.start_changed.connect(planner.set_start)
control_panel.goal_changed.connect(planner.set_goal)

# 权重滑块变化 → 实时重规划 (debounce 300ms)
control_panel.weights_changed.connect(planner.replan_debounced)

# 规划完成 → 更新 3D 视图 + 信息面板
planner.plan_completed.connect(viewer_3d.show_path)
planner.plan_completed.connect(path_info_panel.update)

# 线段列表选中 → 中心线高亮联动
segment_list.current_segment_changed.connect(viewer_3d.highlight_segment)
```

---

## 10. 实施计划

### 10.1 Phase 0: 环境搭建 (0.5天)

| 任务 | 内容 | 预计 |
|------|------|------|
| T0.1 | 安装依赖: `pip install pyvista pyvistaqt PyQt5 numpy scipy` | 0.5h |
| T0.2 | 验证已有 VTK/JSON 数据可正常加载 | 0.5h |
| T0.3 | 验证已有 A* 算法可正常运行 | 0.5h |
| T0.4 | 创建项目目录骨架 (ui/ engine/ render/ utils/) | 1h |

### 10.2 Phase 1: MVP (5天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T1.1 | 新建 `main_qt.py` — 主窗口骨架 (QMainWindow + QSplitter) | F3 | 2h |
| T1.2 | 集成 PyVista QtInteractor 到 3D 视图区域 | F3 | 1h |
| T1.3 | `render/vessel_renderer.py` — 封装血管模型加载与渲染 | F1 | 1h |
| T1.4 | `render/centerline_renderer.py` — 封装中心线分段渲染 | F2 | 1h |
| T1.5 | `ui/segment_list_panel.py` — 扩展已有 CenterlineViewer | F4 | 0.5h |
| T1.6 | `engine/graph_loader.py` — 封装 JSON 图加载 | F5 | 2h |
| T1.7 | `engine/planner.py` — 封装已有 A* 接口 | F6 | 1h |
| T1.8 | `render/path_renderer.py` — 路径管线渲染 + 起终点标记 | F7,F8 | 1h |
| T1.9 | `ui/viewer_3d.py` — 集成点拾取回调，设定起点/终点 | F9 | 2h |
| T1.10 | `engine/path_analyzer.py` — 路径分析 (长度/曲率/半径/可行性) | F10 | 3h |
| T1.11 | `ui/path_info_panel.py` — 路径信息展示面板 | F10 | 2h |
| T1.12 | `ui/control_panel.py` — FCSV 端点下拉加载 | F11 | 2h |
| T1.13 | 整体联调 + 信号/槽连接 + 样式调整 | — | 4h |

### 10.3 Phase 2: 交互增强 (4天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T2.1 | `render/centerline_renderer.py` — 分叉点检测 + 球体标记 | F12 | 3h |
| T2.2 | `render/color_map.py` — 可行性颜色映射 | F13 | 2h |
| T2.3 | `render/path_renderer.py` — 路径按可行性分段着色 | F13 | 2h |
| T2.4 | `engine/planner.py` — 多候选路径搜索 + 并行渲染 | F14 | 4h |
| T2.5 | `ui/viewer_3d.py` — 节点悬浮 tooltip (坐标/属性) | F15 | 3h |
| T2.6 | `render/path_renderer.py` — 安全走廊管状渲染 (TubeFilter) | F16 | 5h |
| T2.7 | `ui/control_panel.py` — 代价权重 QSlider × 5 + 触发重规划 | F17 | 3h |

### 10.4 Phase 3: 高级功能 (3天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T3.1 | 集成 `preprocess/BSplineSmoother.py` 路径平滑 | F18 | 2h |
| T3.2 | 路径曲率热力图着色 + colorbar | F19 | 3h |
| T3.3 | matplotlib FigureCanvas 嵌入 — 路径剖面图 | F20 | 4h |
| T3.4 | `utils/data_export.py` — 导出路径 JSON/CSV | F21 | 2h |
| T3.5 | 场景状态保存/恢复 (JSON 序列化) | F22 | 3h |
| T3.6 | 手动选段导航 — 多段点选 + 跨段 A* 拼接 | F23 | 4h |

---

## 11. 关键风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 真实血管图 ~3000+ 节点，A* 性能 | 规划延迟 >200ms | 已有 Python A* 验证 ≤100ms；使用预计算 dist_to_goal 启发式 |
| PyVista 大量线段渲染性能 | 帧率下降 | 中心线默认管线渲染 + LOD；分段加载 |
| PyVistaQt 与 PyQt5 版本兼容 | 启动崩溃 | 固定版本组合: pyvista==0.43, pyvistaqt==0.11, PyQt5==5.15 |
| 中心线分支拓扑中断 | 路径规划失败 | 预检查拓扑连通性；标记断裂点 (已有 graph_repair 流程) |
| 3D 点拾取精度不足 | 选点偏移 | PyVista `enable_point_picking` + KDTree 吸附最近中心线节点 |
| 图邻接表与中心线坐标不一致 | 路径渲染错位 | 统一从 centerline_vessel_net.json 加载节点坐标；校验节点数一致性 |

---

## 12. 验收标准

### 12.1 功能验收

- [x] 连通子图内任意两点路径规划成功率 ≥ 99%（已有 Python A* 验证）
- [ ] Qt 版 A* 结果与已有 `a_star.py` 独立运行结果一致
- [ ] 3D 场景交互帧率 ≥ 30 FPS（PyVista 关闭平滑渲染）
- [ ] 应用启动加载数据 < 3s
- [ ] 单次路径计算 < 200ms（3000节点图）
- [ ] 路径规划结果可复现（相同输入→相同输出）

### 12.2 UI 验收

- [ ] 支持鼠标旋转/缩放/平移 (PyVista 内建)
- [ ] 3D 点选设定起点/终点，吸附最近中心线节点
- [ ] 路径颜色编码正确 (可行性分段着色)
- [ ] 信息面板数据实时更新
- [ ] 窗口最小尺寸 1024×768

### 12.3 数据验收

- [ ] 血管模型正确显示（形状/位置与 3D Slicer 一致）
- [ ] 中心线拓扑与源数据一致
- [ ] 路径不穿出血管壁（肉眼判断）
- [ ] 线段列表项与实际中心线分段一一对应

---

## 13. 里程碑

```
Day 1-2: Phase 0 环境搭建 + 主窗口骨架 + 血管/中心线渲染
        └── Milestone M1: Qt 窗口可见血管模型 + 中心线

Day 3-7: Phase 1 MVP 开发 + 路径规划闭环
        ├── A* 集成 + 规划接口封装
        ├── 路径渲染 + 起终点标记
        ├── 3D 点拾取交互
        ├── 路径信息面板
        ├── 控制面板 (起终点选择 + 权重调节)
        └── Milestone M2: 完整路径规划闭环 (选点 → 规划 → 渲染 → 数据显示)

Day 8-11: Phase 2 交互增强
        ├── 分叉点可视化
        ├── 可行性颜色编码
        ├── 多候选路径对比
        ├── 安全走廊渲染
        ├── 代价权重实时调节
        └── Milestone M3: 交互完整的演示系统

Day 12-14: Phase 3 高级功能 + 调优
        ├── B样条路径平滑
        ├── 曲率热力图
        ├── 路径剖面图 (matplotlib)
        ├── 数据导出 + 场景保存
        └── Milestone M4: 可交付演示 Demo
```

---

## 14. 附录

### A. 与 INDEX.md 完整系统对应关系

| 完整系统组件 | Demo 对应 | 状态 |
|-------------|-----------|------|
| Main DSA View | — | 不包含 |
| 3D Navigation Assistant | Viewer3D | ✅ 核心交付 |
| Top Info Bar | TopInfoBar (QFrame) | ✅ |
| Bottom Status Bar | QStatusBar | ✅ |
| 控制面板 | ControlPanel | ✅ |
| 安全面板 | — | 不包含 |
| LLM Chat | — | 不包含 |
| 全局规划器 | a_star.py | ✅ 核心算法 |
| 局部规划器 | BSplineSmoother | 🔶 简化版 (仅平滑) |
| 安全监督器 | — | 不包含 |
| 状态估计器 | — | 不包含 |
| 瑞鈊跟踪设备接口 | — | 不包含 (硬件未接入) |
| ROS2 桥接层 | — | 不包含 |

### B. 后续演进路径

```
Phase 1-3 (本计划: 纯路径规划3D演示)
        │
        ▼
Phase 4: WebSocket + FastAPI 后端
  ├── 新建 backend/ (FastAPI + WebSocket)
  ├── 路径规划引擎迁移至后端 (Python 原生复用，无需移植)
  ├── HTTP API 对接: /api/plan, /api/case/{id}/...
  ├── WebSocket 实时推送: robot_pose, path_update, safety_event
  ├── 前端新增 services/websocket.py (Qt QWebSocket 或 asyncio)
  └── 前端保留离线规划能力 (独立模式)
        │
        ▼
Phase 5: 瑞鈊硬件联调
  ├── ROS2 hardware_interface_node (C++) ─ 瑞鈊SDK
  ├── ROS2 state_estimator_node (C++)
  ├── ROS2 Bridge (rclpy → FastAPI → WebSocket)
  ├── 前端新增 TipPoseOverlay (器械实时位姿球体 + 方向矢量)
  ├── 前端新增 PredictionTrajectory (前瞻200ms轨迹线段)
  ├── 前端新增 ConnectionStatus (设备/传感器/网卡) → QStatusBar 扩展
  └── 安全状态机联调 (SAFE_HOLD / EMERGENCY_STOP 触发)
        │
        ▼
Phase 6: DSA 影像集成
  ├── 引入 Cornerstone3D (DICOM 2D 渲染)
  ├── 或 PyVista + VTK 体渲染 (3D Volume Rendering)
  ├── 2D/3D 配准可视化 (ICP / CPD / 中心线配准)
  └── 安全走廊 DSA 投影叠加
        │
        ▼
Phase 7: 完整术中导航系统 (按 INDEX.md 全量交付)
  ├── 安全监督器UI (风险等级/限速/制动/回退)
  ├── 人工接管交互
  ├── VLA 动作候选项显示
  ├── LLM 解释面板
  └── 全量事件日志追溯面板
```

### C. 瑞鈊硬件联调数据链路 (Phase 5)

#### C.1 Qt 前端数据通道

当进入 Phase 5 瑞鈊联调时，Qt 前端新增 WebSocket 客户端：

```python
# ui/websocket_client.py (新增)
import asyncio
import json
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class WebSocketClient(QObject):
    # 10-30 Hz
    robot_pose_received = pyqtSignal(dict)     # {timestamp, position, direction, path_index, status}
    # 1-5 Hz
    path_update_received = pyqtSignal(dict)    # {global_path_id, local_traj_id, feasibility, replan_reason}
    # 事件触发
    safety_event_received = pyqtSignal(dict)   # {risk_level, distance_to_wall, distance_to_path, action}
    # 设备连接状态 (事件触发)
    device_status_received = pyqtSignal(dict)  # {connection, sensor_online, net_linked, calibration_status}
```

#### C.2 前端新增视图组件

```text
path_planing/
  ui/
    connection_status_panel.py    # 设备/传感器/网卡状态 (QGroupBox)
    safety_panel.py               # d_wall, d_path, 风险等级, 限速/制动
  render/
    tip_pose_overlay.py           # 器械尖端实时位姿 (球体 + 方向矢量 + 历史轨迹)
    prediction_trajectory.py      # 预测轨迹 200-500ms (红色虚线)
    safety_corridor.py            # 安全走廊可视化 (管状半透明)
```

#### C.3 瑞鈊SDK → Qt 前端完整数据流

```text
瑞鈊设备 (硬件)
    │
    ├─ updateDeviceInfo/getDeviceInfo  → 设备发现
    ├─ connect/disconnect              → 物理链路管理
    ├─ startTracking/stopTracking      → 跟踪启停
    ├─ trackingUpdate/getTrackingData  → SensorToolTrackingData
    ├─ getConnectionStatus             → SensorConnectionStatus
    ├─ getSensorConnected              → bool (传感器在线)
    ├─ getNetAdaptorInfo               → SensorNetAdaptorInfo (断连快检)
    ├─ pivotTipCalibration             → Tip坐标标定
    └─ fixedDirCalibration             → 方向标定
            │
            ▼
    hardware_interface_node (ROS2 C++)
      → 发布 /hardware/ruixin_tracking_raw
      → 发布 /hardware/ruixin_connection_status
      → 发布 /hardware/ruixin_sensor_status
      → 发布 /hardware/ruixin_net_status
            │
            ▼
    state_estimator_node (ROS2 C++)
      → 订阅瑞鈊原始数据
      → 坐标转换 (LPS统一)
      → EKF/UKF 滤波融合
      → 时间戳对齐
      → 发布 /state_estimator/tip_pose
      → 发布 /state_estimator/tip_direction
      → 发布 /state_estimator/tip_velocity
      → 发布 /state_estimator/tracking_confidence
            │
            ▼
    ROS2 Bridge (Python rclpy → FastAPI)
      → 订阅 ROS2 Topics
      → 序列化为 JSON
      → WebSocket 推送至 Qt 前端
            │
            ▼
    Qt 前端 (PyQt5 + PyVista)
      → websocket_client.py 接收消息
      → QTimer 驱动渲染更新 (30 fps)
      → tip_pose_overlay 更新尖端位姿
      → prediction_trajectory 更新预测轨迹
      → safety_panel 更新风险信息
      → connection_status_panel 更新设备状态
      → QStatusBar 显示连接状态图标
```

#### C.4 安全机制 (硬件级)

```text
瑞鈊设备
    → getNetAdaptorInfo (linked=False) → 硬件断连快检 (<100ms)
    → watchdog_node (ROS2 C++) → 心跳监控
    → safety_supervisor_node → SAFE_HOLD / EMERGENCY STOP
    → Qt 前端:
        ├── connection_status_panel 红色告警
        ├── QStatusBar 设备断连图标
        └── 弹出 SAFE_HOLD 覆盖层 (阻断操作)
```

### D. 参考文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 技术设计文档 | `INDEX.md` | 血管介入导航系统完整架构 |
| 瑞鈊SDK说明 | `瑞鈊SDK说明书Windows C++版1.0.2.md` | 跟踪设备接口 |
| 已有 A* 规划 | `vascular_path_planning/planning/a_star.py` | 核心算法 |
| 已有 PyVista 可视化 | `path_planing/visualize.py` | 3D 可视化 + Qt 线段选择器 |
| 图数据 | `source/graphs/centerline_vessel_net.json` | 有向图 (~3000+ 节点) |
| 血管模型 | `source/vtk/blood_vessels.vtk` | 3D 血管表面 |
| 中心线 | `source/vtk/Centerline_curves_merged.vtk` | 中心线骨架 |
| B样条平滑 | `preprocess/BSplineSmoother.py` | 路径后处理 |

---

> **文档版本**: v2.0  
> **最后更新**: 2026-05-11  
> **技术路线**: 方案 C — Python + PyVista + Qt  
> **下一阶段**: 进入开发实施，按 Phase 0 → Phase 1 → Phase 2 → Phase 3 逐步交付


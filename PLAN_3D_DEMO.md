# 血管路径规划 3D 演示前端 —— 开发计划

> 版本: v1.0  
> 状态: 未开展硬件联调联试，仅路径规划3D演示  
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
| **A: React + vtk.js** | vtk.js | TypeScript/JS | 与 INDEX.md 技术栈一致；医学影像社区标准；支持 Volume Rendering | 学习曲线陡；Bundle 体积大 |
| **B: React + Three.js** | Three.js | TypeScript/JS | 生态丰富；性能好；社区活跃 | 非医学专用；需自行封装管线渲染 |
| **C: 纯 Python (pyvista)** | PyVista/VTK | Python | 已有代码可直接复用；开发快 | 非 Web 前端；无法浏览器访问 |

### 2.2 推荐方案

**Phase 1 (快速验证)**: 方案 C — 扩展现有 `path_planing/` + PyVista，快速出可交互演示  
**Phase 2 (Web 部署)**: 方案 B — Three.js + React，实现浏览器可访问的 3D 演示  
**Phase 3 (与系统对齐)**: 方案 A — 与 INDEX.md 技术栈对齐，为后续合并做准备

本计划以 **Phase 1 + Phase 2** 为核心交付。

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
│                  UI Layer (React)                    │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 3D Viewer │ │  Info    │ │  Control Panel    │  │
│  │ (Three.js)│ │  Panel   │ │ (权重/起终点/模式) │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│               State Management (Zustand)             │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Scene     │ │ Planner  │ │ UI State          │  │
│  │ Store     │ │ Store    │ │ Store             │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│                  Logic Layer (纯函数)                │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Graph     │ │ A*       │ │ Path Post-        │  │
│  │ Loader    │ │ Planner  │ │ Processor         │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│                  Data Layer                          │
│  ┌───────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ VTK       │ │ JSON     │ │ Static Assets     │  │
│  │ Loader    │ │ Graph    │ │ (glTF/glb)        │  │
│  └───────────┘ └──────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 4.2 数据流

```
VTK文件 → VTKLoader → Three.js Mesh/Line → 3D Scene
JSON图  → GraphLoader → Adjacency Map → A* Planner
                    ↓
              中心线点云 → KDTree → 3D点选映射 → 起终点
                    ↓
            A* 搜索结果 → 路径节点序列 → PathRenderer → 路径可视化
                    ↓
            Path Info Calculator → 路径统计 → Info Panel
```

---

## 5. 功能清单

### Phase 1: 核心渲染 + 路径规划 (MVP)

| ID | 功能 | 优先级 | 预计工时 |
|----|------|--------|----------|
| F1 | 血管模型 3D 渲染 (半透明表面) | P0 | 4h |
| F2 | 中心线骨架渲染 (管线/线段) | P0 | 4h |
| F3 | 分支拓扑可视化 (分叉点高亮) | P0 | 3h |
| F4 | 3D 场景基础交互 (旋转/缩放/平移) | P0 | 2h |
| F5 | JSON 图加载 + 邻接表构建 | P0 | 3h |
| F6 | A* 路径规划 (基于真实血管图) | P0 | 4h |
| F7 | 规划路径 3D 高亮显示 | P0 | 3h |
| F8 | 起点/终点标记 (球体/箭头) | P0 | 2h |
| F9 | 路径统计面板 (长度/节点数/曲率) | P1 | 3h |

### Phase 2: 交互 + 可视化增强

| ID | 功能 | 优先级 | 预计工时 |
|----|------|--------|----------|
| F10 | 3D 点拾取设定起点 | P1 | 4h |
| F11 | 3D 点拾取设定终点 | P1 | 2h |
| F12 | 预设端点下拉选择 (基于 FCSV) | P1 | 3h |
| F13 | 路径可行性颜色编码 (Green/Yellow/Orange/Red) | P1 | 4h |
| F14 | 线段列表 + 点击高亮 (类 Qt 版) | P1 | 5h |
| F15 | 多候选路径对比显示 | P2 | 4h |
| F16 | 路径节点属性悬浮提示 | P2 | 3h |
| F17 | 安全走廊可视化 (管状半透明) | P2 | 5h |

### Phase 3: 高级功能

| ID | 功能 | 优先级 | 预计工时 |
|----|------|--------|----------|
| F18 | 代价权重实时调节面板 | P2 | 4h |
| F19 | 路径平滑后处理 (B-spline) | P2 | 4h |
| F20 | 曲率可视化 (路径着色) | P2 | 3h |
| F21 | 路径剖面图 (半径/曲率曲线) | P3 | 5h |
| F22 | 导出路径数据 (JSON/CSV) | P3 | 2h |
| F23 | 预设场景快照 (URL参数) | P3 | 3h |

---

## 6. 项目目录结构

```
vascular-path-demo/
├── public/
│   └── data/
│       ├── blood_vessels.glb          # 转换后的血管模型
│       ├── centerline_curves.glb      # 转换后的中心线
│       └── centerline_vessel_net.json # 有向图 (已有)
├── src/
│   ├── components/
│   │   ├── Viewer3D/
│   │   │   ├── Viewer3D.tsx           # 3D 场景主组件
│   │   │   ├── VesselMesh.tsx         # 血管表面渲染
│   │   │   ├── CenterlineRenderer.tsx # 中心线骨架
│   │   │   └── PathOverlay.tsx        # 路径叠加层
│   │   ├── Panels/
│   │   │   ├── ControlPanel.tsx       # 控制面板 (起终点/权重)
│   │   │   ├── PathInfoPanel.tsx      # 路径信息展示
│   │   │   └── SegmentList.tsx        # 线段列表
│   │   └── Layout/
│   │       └── AppLayout.tsx          # 总体布局
│   ├── engine/
│   │   ├── a_star.ts                  # A* 算法 (JS 移植)
│   │   ├── graph.ts                   # 图加载 + 邻接表
│   │   ├── kd_tree.ts                 # KDTree (点→节点映射)
│   │   └── path_smoother.ts           # 路径平滑
│   ├── loader/
│   │   ├── vtk_loader.ts             # VTK 文件解析
│   │   └── glb_loader.ts             # glTF/glb 加载
│   ├── store/
│   │   ├── sceneStore.ts             # 场景状态
│   │   └── plannerStore.ts           # 规划状态
│   ├── utils/
│   │   ├── color.ts                   # 颜色编码
│   │   └── math.ts                    # 几何计算
│   ├── types/
│   │   └── index.ts                   # 类型定义
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
└── PLAN_3D_DEMO.md                    # 本计划文档
```

---

## 7. 核心算法设计

### 7.1 A* 路径规划 (移植自 Python)

```typescript
// 类型定义
interface GraphNode {
  id: number;
  position: [number, number, number]; // x, y, z in LPS
}

interface Edge {
  to: number;
  weight: number; // mm 距离
}

interface Graph {
  nodes: GraphNode[];
  adjacency: Map<number, Edge[]>;
}

// A* 接口
function aStar(
  graph: Graph,
  startIdx: number,
  goalIdx: number,
  options?: {
    heuristic?: (a: number, b: number) => number;
    weights?: CostWeights;
  }
): PathResult;

interface CostWeights {
  w_len: number;   // 距离权重 (default: 1.0)
  w_curv: number;  // 曲率惩罚 (default: 0.3)
  w_rad: number;   // 半径惩罚 (default: 0.2)
  w_dir: number;   // 方向惩罚 (default: 0.1)
  w_risk: number;  // 风险惩罚 (default: 0.0)
}

interface PathResult {
  path: [number, number, number][]; // 路径点序列
  totalLength: number;               // 总长度 mm
  totalCost: number;                 // 总代价
  peakCurvature: number;             // 峰值曲率
  minRadius: number;                 // 最小半径
  feasibility: 'green' | 'yellow' | 'orange' | 'red';
}
```

### 7.2 启发式函数

```typescript
// 使用预计算的 FlowDistance 替代欧几里得距离
// 若无可预计算距离，fallback 为欧几里得距离
function euclideanHeuristic(
  a: [number, number, number],
  b: [number, number, number]
): number {
  return Math.sqrt(
    (b[0] - a[0]) ** 2 +
    (b[1] - a[1]) ** 2 +
    (b[2] - a[2]) ** 2
  );
}
```

### 7.3 KDTree 加速最近点查找

```typescript
// 3D 点选 → 最近中心线节点
// 用于交互式起终点设定
class KDTree {
  build(points: [number, number, number][]): void;
  nearest(
    query: [number, number, number]
  ): { index: number; distance: number };
}
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

### 8.2 渲染样式

| 对象 | 样式 | 说明 |
|------|------|------|
| 血管表面 | 半透明红色 `rgba(255,0,0,0.3)` | MeshPhysicalMaterial |
| 中心线 | 深灰 `#333`，lineWidth=1.5 | LineBasicMaterial |
| 规划路径 | 亮绿 `#00FF00`，lineWidth=4 | 管线渲染/粗线 |
| 起点 | 蓝色球体 r=2mm | SphereGeometry |
| 终点 | 绿色球体 r=2mm | SphereGeometry |
| 分叉点 | 黄色小点 r=1mm | PointsMaterial |
| 候选路径 | 虚线样式 | LineDashedMaterial |

### 8.3 坐标系

- 系统: **LPS** (Left-Posterior-Superior)
- 单位: **mm**
- 场景默认朝向: 相机初始位置设为俯视 LPS 坐标系最佳观察角度

---

## 9. UI 布局设计

### 9.1 总体布局

```
┌─────────────────────────────────────────────────────┐
│ Top Bar: 标题 | 模式 | 数据信息                       │
├───────────────────────────────┬─────────────────────┤
│                               │  Path Info Panel    │
│       3D Viewer               │  ┌───────────────┐  │
│      (Three.js Canvas)        │  │ 路径长度: xxx  │  │
│                               │  │ 节点数:   xxx  │  │
│   🟢 Vessel Model             │  │ 曲率峰值: xxx  │  │
│   ⚫ Centerlines              │  │ 最小半径: xxx  │  │
│   🟢 Planned Path             │  │ 可行性:   🟡   │  │
│   🔵 Start Marker             │  └───────────────┘  │
│   🟢 Goal Marker              │                     │
│                               │  Control Panel     │
│                               │  ┌───────────────┐  │
│                               │  │ 起点: [选择]   │  │
│                               │  │ 终点: [选择]   │  │
│                               │  │ w_len: ──●──  │  │
│                               │  │ w_curv: ──●── │  │
│                               │  │ w_rad:  ──●── │  │
│                               │  │ [计算路径]     │  │
│                               │  └───────────────┘  │
│                               │                     │
│                               │  Segment List       │
│                               │  ┌───────────────┐  │
│                               │  │ segment_0 (42) │  │
│                               │  │ segment_1 (38) │  │
│                               │  │ segment_2 (55) │  │
│                               │  │ ...            │  │
│                               │  └───────────────┘  │
├───────────────────────────────┴─────────────────────┤
│ Bottom Bar: 帧率 | 相机位置 | 选中节点信息            │
└─────────────────────────────────────────────────────┘
```

### 9.2 组件树

```
AppLayout
├── TopBar
│   ├── Title ("血管路径规划 3D 演示")
│   ├── ModeIndicator
│   └── DataInfo (节点数/边数)
├── SplitPane (70/30)
│   ├── Viewer3D (左侧 70%)
│   │   ├── VesselMesh
│   │   ├── CenterlineRenderer
│   │   │   └── SegmentLine[] (每个线段一个 Line)
│   │   ├── PathOverlay
│   │   │   ├── PathTube (路径管线)
│   │   │   └── PathDots (路径节点)
│   │   ├── BifurcationPoints (分叉点标记)
│   │   └── Markers
│   │       ├── StartMarker
│   │       └── GoalMarker
│   └── RightPanel (右侧 30%)
│       ├── PathInfoPanel
│       │   ├── LengthDisplay
│       │   ├── NodesDisplay
│       │   ├── CurvatureDisplay
│       │   ├── RadiusDisplay
│       │   └── FeasibilityBadge
│       ├── ControlPanel
│       │   ├── StartPointSelector
│       │   ├── GoalPointSelector
│       │   ├── WeightSliders
│       │   └── CalculateButton
│       └── SegmentList
│           └── SegmentItem[]
└── BottomBar
    ├── FPS
    ├── CameraPosition
    └── SelectedNodeInfo
```

---

## 10. 实施计划

### 10.1 Phase 0: 环境搭建 (1天)

| 任务 | 内容 | 预计 |
|------|------|------|
| T0.1 | 初始化 Vite + React + TypeScript 项目 | 1h |
| T0.2 | 安装依赖: three, @react-three/fiber, @react-three/drei, zustand | 0.5h |
| T0.3 | 配置 ESLint + Prettier + 路径别名 | 0.5h |
| T0.4 | VTK → glTF 数据转换脚本 (Python 一次运行) | 2h |
| T0.5 | 验证数据加载正确性 | 1h |

### 10.2 Phase 1: MVP (5天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T1.1 | 实现 GLB Loader + 血管模型渲染 (VesselMesh) | F1 | 4h |
| T1.2 | 实现中心线渲染器 (CenterlineRenderer) | F2 | 4h |
| T1.3 | 实现分叉点检测 + 标记 | F3 | 3h |
| T1.4 | 集成 OrbitControls + 场景灯光/相机 | F4 | 2h |
| T1.5 | 实现 JSON 图加载 + Graph 类 | F5 | 3h |
| T1.6 | 移植 A* 算法到 TypeScript | F6 | 4h |
| T1.7 | 实现路径渲染 (PathOverlay) | F7 | 3h |
| T1.8 | 起终点标记 + 预设端点加载 | F8 | 2h |
| T1.9 | 实现 PathInfoPanel | F9 | 3h |
| T1.10 | 整体联调 + 样式调整 | — | 4h |

### 10.3 Phase 2: 交互增强 (4天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T2.1 | 3D Raycaster 点拾取 + 吸附最近节点 | F10, F11 | 4h |
| T2.2 | 预设端点下拉菜单 | F12 | 3h |
| T2.3 | 路径颜色编码 (可行性分段着色) | F13 | 4h |
| T2.4 | SegmentList 组件 + 高亮联动 | F14 | 5h |
| T2.5 | 多候选路径对比 | F15 | 4h |
| T2.6 | 节点悬浮 Tooltip | F16 | 3h |
| T2.7 | 安全走廊管状渲染 | F17 | 5h |

### 10.4 Phase 3: 高级功能 (3天)

| 任务 | 对应功能 | 预计 |
|------|----------|------|
| T3.1 | 代价权重面板 + 实时重规划 | F18 | 4h |
| T3.2 | B-spline 路径平滑 (WASM 或 JS 实现) | F19 | 4h |
| T3.3 | 路径曲率热力图着色 | F20 | 3h |
| T3.4 | 路径剖面图 (Canvas 2D 绘制) | F21 | 5h |
| T3.5 | 数据导出功能 | F22 | 2h |
| T3.6 | URL 参数场景恢复 | F23 | 3h |

---

## 11. 关键风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| VTK 文件浏览器端无法直接加载 | 阻断渲染 | Phase 0 预转换为 glTF/glb 格式 |
| 真实血管图 ~3000+ 节点，A* 性能 | 交互卡顿 | 使用 BinaryHeap + Best-First 优化；预计算启发式距离 |
| Three.js 管线渲染 (TubeGeometry) 性能 | 大量线段帧率下降 | 使用 Line + LineMaterial 折中；分块加载 |
| 中心线分支拓扑中断 | 路径规划失败 | 预检查拓扑连通性；标记断裂点 |
| 3D 点拾取精度不足 | 选点偏移 | Raycaster + KDTree 吸附最近中心线节点 |

---

## 12. 验收标准

### 12.1 功能验收

- [x] 连通子图内任意两点路径规划成功率 ≥ 99%（已有 Python A* 验证）
- [ ] Web 版 A* 与 Python 版结果一致（相同起终点，路径相同）
- [ ] 3D 场景交互帧率 ≥ 30 FPS（目标硬件: 笔记本集显）
- [ ] 首屏加载 < 3s
- [ ] 单次路径计算 < 200ms（3000节点图）
- [ ] 路径规划结果可复现（相同输入→相同输出）

### 12.2 UI 验收

- [ ] 支持鼠标旋转/缩放/平移
- [ ] 支持触控板手势
- [ ] 路径颜色编码正确
- [ ] 信息面板数据正确
- [ ] 响应式布局（≥1280x720）

### 12.3 数据验收

- [ ] 血管模型正确显示（形状/位置与 3D Slicer 一致）
- [ ] 中心线拓扑与源数据一致
- [ ] 路径不穿出血管壁（肉眼判断）

---

## 13. 里程碑

```
Week 1: 环境搭建 + 数据转换 + 3D 场景基础渲染
        └── Milestone M1: 血管模型 + 中心线可见

Week 2: A* 移植 + 路径规划联调 + 基础信息面板
        └── Milestone M2: 完整路径规划闭环 (MVP)

Week 3: 交互增强 (点选/列表联动/颜色编码/安全走廊)
        └── Milestone M3: 交互完整的演示系统

Week 4: 高级功能 + 性能优化 + 文档
        └── Milestone M4: 可交付演示 Demo
```

---

## 14. 附录

### A. 与 INDEX.md 完整系统对应关系

| 完整系统组件 | Demo 对应 | 状态 |
|-------------|-----------|------|
| Main DSA View | — | 不包含 |
| 3D Navigation Assistant | Viewer3D | ✅ 核心交付 |
| Top Info Bar | TopBar (简化) | ✅ |
| Bottom Status Bar | BottomBar (简化) | ✅ |
| 控制面板 | ControlPanel | ✅ |
| 安全面板 | — | 不包含 |
| LLM Chat | — | 不包含 |
| 全局规划器 | a_star.ts | ✅ 核心算法 |
| 局部规划器 | path_smoother.ts | 🔶 简化版 |
| 安全监督器 | — | 不包含 |
| 状态估计器 | — | 不包含 |

### B. 后续演进路径

```
Phase 1-3 (本计划: 纯路径规划3D演示)
        │
        ▼
Phase 4: WebSocket + FastAPI 后端
  ├── 新建 backend/ (FastAPI + WebSocket)
  ├── 前端新增 services/websocket.ts
  ├── HTTP API 对接: /api/plan, /api/case/{id}/...
  ├── 路径规划引擎迁移至后端 (Python 原生复用)
  └── 前端保留离线规划能力 (独立模式)
        │
        ▼
Phase 5: 瑞鈊硬件联调 (关键技术选型见 §2.3)
  ├── ROS2 hardware_interface_node (C++) ─ 瑞鈊SDK
  ├── ROS2 state_estimator_node (C++)
  ├── ROS2 Bridge (rclpy → FastAPI → WebSocket)
  ├── 前端新增 TipPoseOverlay (器械实时位姿)
  ├── 前端新增 PredictionTrajectory (前瞻200ms轨迹)
  └── 前端新增 ConnectionStatus (设备/传感器/网卡)
        │
        ▼
Phase 6: DSA 影像集成
  ├── 引入 Cornerstone3D (与 Three.js 共存)
  ├── MainDSAView (替代当前 3D Viewer 为主视图)
  ├── 2D/3D 配准可视化
  └── 安全走廊 DSA 投影叠加
        │
        ▼
Phase 7: 完整术中导航系统
  ├── 安全监督器UI (风险等级/限速/制动/回退)
  ├── 人工接管交互
  ├── VLA 动作候选项显示
  ├── LLM 解释面板
  └── 全量事件日志追溯面板
```

### C. 瑞鈊硬件联调架构细节

#### C.1 前端新增数据通道

```typescript
// src/services/websocket.ts
interface WebSocketMessages {
  // 10-30 Hz
  robot_pose: {
    timestamp: number;
    position: [number, number, number];   // LPS, mm
    direction: [number, number, number];  // 单位向量
    path_index: number;
    status: 'idle' | 'navigating' | 'hold' | 'retract';
  };
  // 1-5 Hz
  path_update: {
    global_path_id: string;
    local_traj_id: string;
    feasibility: 'green' | 'yellow' | 'orange' | 'red';
    replan_reason: string | null;
  };
  // 事件触发
  safety_event: {
    risk_level: 'warning' | 'danger' | 'emergency';
    distance_to_wall: number;
    distance_to_path: number;
    action: 'speed_limit' | 'stop' | 'retract' | 'safe_hold';
  };
  // 设备连接状态 (事件触发)
  device_status: {
    connection: 'connected' | 'disconnected' | 'interrupted';
    sensor_online: boolean;
    net_linked: boolean;
    calibration_status: 'normal' | 'abnormal';
  };
}
```

#### C.2 前端新增组件 (对应对 INDEX.md 12 节前端模块结构)

```text
src/
  components/
    Viewer3D/
      TipPoseOverlay.tsx        # 器械尖端实时位姿
      PredictionTrajectory.tsx  # 预测轨迹 200-500ms
      SafetyCorridor.tsx        # 安全走廊可视化
    Panels/
      SafetyPanel.tsx           # d_wall, d_path, 风险等级, 限速/制动
      ConnectionPanel.tsx       # 设备/传感器/网卡状态
      CalibrationPanel.tsx      # 标定状态 & 误差预警
      VLAStatusPanel.tsx        # VLA 高层动作候选项
      LLMChatPanel.tsx          # LLM 交互面板
    Layout/
      TopInfoBar.tsx            # 控制模式/机器人/安全/规划状态
      BottomStatusBar.tsx       # 坐标/时间同步/节点健康/报警
```

#### C.3 瑞鈊SDK → 前端完整数据链路

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
    ROS2 Bridge (Python rclpy)
      → 订阅 ROS2 Topics
      → 序列化为 JSON
      → WebSocket 推送至前端
            │
            ▼
    前端 (React + Three.js)
      → websocket.ts 接收消息
      → plannerStore / safetyStore 更新状态
      → TipPoseOverlay 渲染尖端位姿
      → PredictionTrajectory 渲染预测轨迹
      → SafetyPanel 更新风险信息
      → ConnectionPanel 更新设备状态
```



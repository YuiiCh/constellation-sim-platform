# 星座仿真平台（Constellation Simulation Platform）

实时 / 未来 / 合成星座展示与**地面区域覆盖仿真**的一体化平台。前端 Vue3 + Vite + TypeScript + Cesium + ECharts，后端 Python + FastAPI + SQLite + NumPy。

> 本仓库为单端口可部署形态：后端同时托管前端构建产物，外部通过单一端口即可访问。

---

## 1. 功能范围

- **星座**：千帆星座、国网星座（实时/合成轨道根数兜底）、千帆一期（规划）、国网一期（规划，Walker-Delta / Walker-Star）。支持实时星座与未来/合成星座切换。
- **实时数据**：celestrak 持续拉取框架（网络不可达时自动降级为基于真实星座设计参数的合成轨道根数，平台完全可用）；space-track 历史星历按需查询（凭据缺失/限流有明确提示，不崩溃）。
- **时间轴**：播放/暂停、日期、时间、24h 拖动轴、实时按钮（默认选中、修改后变灰、点击恢复同步）、倍率（1/10/60/600）、时区。
- **Cesium 渲染**：黑蓝玻璃感纯色地球、白色经纬网与仿真区域边界（3km 高度）、卫星点（PointPrimitiveCollection 高效图元）、点击高亮（脉冲动画）、多选、轨道线显示（Web Worker 计算，不阻塞主线程）。
- **覆盖仿真**：H3 网格化地面区域 + 简单仰角规则 + 复杂 C/dBm 功率规则；链路预算物理量齐备；NumPy 向量化；**分阶段记录耗时**（传播/仰角/功率/聚合）；结果持久化，前端 H3 六边形着色 + 覆盖连线 + 点击网格查看详情 + 覆盖率时序图。
- **任务管理**：创建 / 查询 / 删除、运行中数量、历史任务结果可视化。
- **端到端测试**：Playwright 覆盖关键路径。

---

## 2. 目录结构

```
backend/             FastAPI 后端（venv + SQLite + NumPy）
  app/
    config.py       环境变量与默认参数
    database.py     SQLAlchemy 引擎/会话
    models.py       ORM 表（9 张）
    schemas.py      Pydantic 契约
    orbital.py      轨道传播（J2 开普勒，NumPy）
    constellations.py 星座定义 + Walker 合成
    h3grid.py       H3 地面网格
    coverage.py     覆盖仿真引擎（分阶段 + 向量化）
    celestrak.py    celestrak 拉取（优雅降级）
    spacetrack.py   space-track 查询（明确提示）
    taskrunner.py   仿真任务后台执行
    seed.py         种子数据
    main.py         API + 静态托管
frontend/           Vue3 + Vite + Cesium + ECharts
  src/components/    UI 组件
  src/workers/       轨道计算 Web Worker
  src/store/        Pinia 状态
  tests/e2e/        Playwright 测试
docs/coverage_analysis_design.md  覆盖仿真设计文档
scripts/dev|prod/   启停脚本（热重载 / 单端口部署）
.env.example        环境变量示例
```

---

## 3. 快速开始

### 开发模式（前后端热重载）
```bash
# 终端 1
bash scripts/dev/start.sh
# 打开 http://127.0.0.1:5173 （前端 vite，/api 经代理转发到 8080）
bash scripts/dev/stop.sh   # 停止
```

### 生产 / 本地部署（单端口）
```bash
bash scripts/prod/start.sh   # 构建前端并由后端在 0.0.0.0:8080 统一托管
# 浏览器访问 http://<host>:8080
bash scripts/prod/stop.sh    # 停止
```

### 环境变量
复制 `.env.example` 为 `.env` 按需修改。全部变量均带默认值；关键项：
`PORT`、`CELESTRAK_ENABLED`、`CELESTRAK_FETCH_INTERVAL`、仿真默认参数（`DEFAULT_H3_RES`、`DEFAULT_EL_MIN_DEG`、`DEFAULT_C_MIN_DBM` 等）。

---

## 4. 主要 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/config` | 全局配置（倍率、默认参数、时区） |
| GET | `/api/constellations` | 星座列表 |
| GET | `/api/constellations/{id}/satellites` | 卫星（默认仅稳定壳层，支持壳层筛选） |
| GET | `/api/constellations/{id}/shells` | 壳层 |
| GET | `/api/satellites/{norad_id}` | 卫星详情 |
| GET | `/api/constellations/{id}/propagate?t=ISO` | 指定时刻卫星位置 |
| POST | `/api/simulations` | 创建覆盖仿真任务 |
| GET | `/api/simulations` | 任务列表 |
| GET | `/api/simulations/{id}` | 任务详情 |
| DELETE | `/api/simulations/{id}` | 删除任务 |
| GET | `/api/simulations/{id}/summary` | 汇总指标 |
| GET | `/api/simulations/{id}/frames` | 覆盖帧时间步 |
| GET | `/api/simulations/{id}/frame/{step}` | 某帧 H3 覆盖样本 |
| POST | `/api/constellations/{id}/regenerate` | 合成星座 Walker 参数重生成 |
| POST | `/api/admin/fetch/celestrak` | 触发 celestrak 拉取 |
| POST | `/api/spacetrack/query` | space-track 历史星历查询 |

任务状态：`pending / running / succeeded / failed / cancelled`，含进度、错误信息、分阶段耗时。

---

## 5. 覆盖仿真设计要点

详见 `docs/coverage_analysis_design.md`。要点：
- **H3 网格**：Uber H3 多边形填充，默认分辨率 4，区域可调（默认中国主体/中部框）。
- **简单规则**：仰角 `el ≥ el_min`（默认 10°）。
- **复杂规则**：链路预算 `C/dBm = EIRP − L_fs − L_atm − L_pol − L_point`，默认 EIRP 47 dBW、12 GHz、C/dBm 门槛 −100 dBm；`el ≥ el_min` 且 `C/dBm ≥ C_min` 方为覆盖。
- **分阶段耗时**：传播 / 仰角 / 功率 / 聚合，结果可复现（确定性计算）。

---

## 6. 测试

```bash
cd frontend
npx playwright test        # 端到端关键路径
```

覆盖：页面加载与地球渲染、星座切换与筛选、时间轴实时按钮逻辑、创建覆盖仿真并查看结果、任务删除与历史可视化。

后端单元测试（可选）：
```bash
cd backend && ./venv/bin/python -m pytest
```

---

## 7. 备注

- celestrak 在本沙箱网络不可达，已自动降级为合成轨道根数；真实网络下启用 `CELESTRAK_ENABLED=true` 将持续拉取并持久化真实星历。
- space-track 查询需用户提供凭据（前端弹窗输入），缺失或限流时给出明确提示且不崩溃。
- 默认仿真区域为保证分钟级完成采用中部框；可在创建任务向导中扩大区域/提高 H3 分辨率。

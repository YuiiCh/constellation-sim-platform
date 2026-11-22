# 星座仿真平台 · Constellation Simulation Platform

在 3D 地球上展开低轨巨型星座，按时间轴播放卫星运动，并用 **H3 网格 + 仰角 / 链路预算规则** 计算地面区域在给定时间段内的覆盖情况。

前端 Vue 3 + TypeScript + Vite + Cesium + ECharts，后端 FastAPI + SQLAlchemy + SQLite + NumPy。**单端口可部署**：生产模式下后端直接托管前端构建产物。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.4-42B883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)
![Cesium](https://img.shields.io/badge/Cesium-1.118-4C9A2A)
![License](https://img.shields.io/badge/license-未声明-lightgrey)

> **状态**：可运行的个人项目，尚无 CI、容器化与发布包。API 与数据结构在演进中，未承诺向后兼容。

---

## 目录

- [核心能力](#核心能力)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [内置星座](#内置星座)
- [覆盖仿真](#覆盖仿真)
- [API 速查](#api-速查)
- [配置项](#配置项)
- [测试](#测试)
- [常见问题](#常见问题)
- [数据与降级策略](#数据与降级策略)
- [已知限制与后续计划](#已知限制与后续计划)
- [许可](#许可)

---

## 核心能力

| 能力 | 说明 |
|---|---|
| **星座展示** | 千帆、国网（真实星座）+ 千帆一期、国网一期（Walker 合成规划星座），可在实时 / 未来 / 合成形态间切换 |
| **Cesium 渲染** | 纯色玻璃感地球、白色经纬网与仿真区域边界、`PointPrimitiveCollection` 高效卫星图元、点击高亮脉冲、多选、Web Worker 计算轨道线（不阻塞主线程） |
| **时间轴** | 播放 / 暂停、日期与时刻选择、24h 拖动轴、实时同步按钮、1 / 10 / 60 / 600 倍率、时区切换 |
| **覆盖仿真** | H3 六边形地面网格；简单规则（仰角）与复杂规则（C/dBm 链路预算）；NumPy 向量化；分阶段记录耗时 |
| **结果可视化** | H3 网格着色、覆盖连线、点击网格查看明细、覆盖率时序图（ECharts） |
| **任务管理** | 创建 / 查询 / 删除仿真任务，运行中任务数、进度、失败原因、历史结果回看 |
| **星历数据** | celestrak 持续拉取框架（不可达时自动降级为合成轨道根数）；space-track 历史星历按需查询 |
| **端到端测试** | Playwright 覆盖 5 条关键路径 |

---

## 技术栈

| 层 | 选型 |
|---|---|
| 前端框架 | Vue 3 (`<script setup>`) + Pinia + TypeScript 5.5 |
| 构建 | Vite 5 + `vite-plugin-cesium` |
| 可视化 | Cesium 1.118（3D 地球）、ECharts 5.5（时序图） |
| 后端 | FastAPI + Uvicorn + Pydantic v2 + SQLAlchemy 2 |
| 计算 | NumPy（向量化传播与覆盖判定）、H3（网格） |
| 存储 | SQLite（默认 `backend/data/constellation.db`） |
| 测试 | pytest（后端计算）、Playwright（端到端） |

---

## 快速开始

### 前置要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.10+（建议 3.11 / 3.12） | `requirements.txt` 未锁定版本 |
| Node.js | 18+（建议 20 LTS） | Vite 5 与 Playwright 1.47 的最低要求 |
| Bash | — | `scripts/` 下均为 Bash 脚本；Windows 请用 Git Bash 或 WSL |

### 1. 获取代码

```bash
git clone https://github.com/YuiiCh/constellation-sim-platform.git
cd constellation-sim-platform
```

### 2. 安装后端依赖

> ⚠️ **虚拟环境目录名必须是 `venv`**。`scripts/*.sh` 中硬编码了 `./venv/bin/uvicorn`，用 `.venv` 等其它名字脚本会找不到可执行文件。

```bash
cd backend
python -m venv venv

# Linux / macOS / WSL
./venv/bin/pip install -r requirements.txt
# Windows Git Bash
./venv/Scripts/pip install -r requirements.txt

cd ..
```

首次启动会自动建表并写入种子数据，无需手工初始化数据库。

### 3. 安装前端依赖

```bash
cd frontend && npm install && cd ..
```

`dev/start.sh` **不会**自动执行 `npm install`（只有 `prod/start.sh` 会在 `node_modules` 缺失时补装），所以这一步必须先做。

### 4. 启动

**开发模式** — 前后端双进程热重载，`/api` 由 Vite 代理到 8080：

```bash
bash scripts/dev/start.sh
# 打开 http://127.0.0.1:5173
bash scripts/dev/stop.sh
```

**单端口模式** — 构建前端并由后端在 8080 统一托管，适合演示与内网部署：

```bash
bash scripts/prod/start.sh
# 打开 http://<host>:8080
bash scripts/prod/stop.sh
```

脚本会把日志写到 `/tmp/csp_backend.log`、`/tmp/csp_frontend.log`、`/tmp/csp_prod.log`，起不来时先看这里。

**不用脚本时的等价命令：**

```bash
# 终端 1
cd backend && ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
# 终端 2
cd frontend && npm run dev
```

> Windows 用户注意：`scripts/*.sh` 里的 `./venv/bin/uvicorn` 是 POSIX 路径，而 Windows 的 venv 可执行文件位于 `venv/Scripts/`。要么按上面的"等价命令"手动启动（Windows 下改为 `./venv/Scripts/uvicorn.exe`），要么直接用 WSL。

---

## 目录结构

```
backend/                     FastAPI 服务（约 2000 行 Python）
  app/
    config.py                环境变量读取与默认参数（全部带默认值）
    database.py              SQLAlchemy 引擎 / 会话
    models.py                ORM 表定义（星座、壳层、卫星、仿真任务等 9 张）
    schemas.py               Pydantic 请求/响应契约
    orbital.py               轨道传播（J2 摄动 + 开普勒，NumPy 向量化）
    constellations.py        星座目录 + Walker-Delta / Walker-Star 合成
    h3grid.py                H3 地面网格填充
    coverage.py              覆盖仿真引擎（分阶段计时 + 向量化）
    celestrak.py             celestrak 拉取（不可达时优雅降级）
    spacetrack.py            space-track 历史星历查询
    taskrunner.py            仿真任务后台执行与进度更新
    seed.py                  种子数据（首次启动写入）
    main.py                  API 路由 + 前端静态托管
  run.py                     本地启动入口
  tests/test_coverage.py     轨道与覆盖引擎单元测试
frontend/
  src/
    components/              地球视图、时间轴、星座信息、任务栏、结果面板、创建向导等
    workers/orbit.worker.ts  轨道计算 Web Worker
    services/api.ts          后端 API 封装
    store/index.ts           Pinia 状态（时间推进、任务轮询）
    utils/time.ts            时区与时间换算
  tests/e2e/platform.spec.ts Playwright 端到端用例
docs/coverage_analysis_design.md   覆盖仿真设计文档（204 行，含公式与取舍）
scripts/{dev,prod}/          启停脚本
.env.example                 环境变量示例
```

---

## 内置星座

星座目录定义在 `backend/app/constellations.py`，首次启动写入数据库。

| id | 名称 | 类型 | 壳层 | 卫星数 |
|---|---|---|---|---|
| `qianfan` | 千帆星座 | 真实（合成根数兜底） | 1000 km/50°、1000 km/55°、1050 km/60° + 800 km/85°（试验） | 408 + 12 |
| `guowang` | 国网星座 | 真实（合成根数兜底） | 590 km/30°、600 km/50°、610 km/60°、1145 km/85° + 500 km/85°（试验） | 340 + 8 |
| `qianfan-phase1` | 千帆一期（规划） | Walker-Delta 合成 | 1000 km/55°，10 面 × 30 星 | 300 |
| `guowang-phase1` | 国网一期（规划） | Walker-Star 合成 | 600 km/60°，12 面 × 30 星 | 360 |

稳定壳层合计 **1408 颗**；`temporary` 壳层默认不参与展示，需显式选择。

---

## 覆盖仿真

设计细节与公式推导见 [`docs/coverage_analysis_design.md`](docs/coverage_analysis_design.md)，这里只列要点。

**流程**：选定星座与壳层 → 选定地面区域 → 按 H3 分辨率多边形填充得到网格单元 → 以固定采样步长遍历时间 → 对每个单元判定是否被任一卫星覆盖 → 聚合出逐帧结果与时序覆盖率。

**判定规则**

| 规则 | `rule_type` | 判据 |
|---|---|---|
| 简单 | `simple_elevation` | `el ≥ el_min` |
| 复杂 | `complex_power` | `el ≥ el_min` **且** `C/dBm ≥ C_min`，其中 `C = EIRP − L_fs − L_atm − L_pol − L_point` |

**默认参数**（全部可用环境变量覆盖）

| 参数 | 默认值 | 参数 | 默认值 |
|---|---|---|---|
| 采样步长 `DEFAULT_SAMPLE_INTERVAL_S` | 15 s | 频率 `DEFAULT_FREQ_HZ` | 12 GHz |
| 时长 `DEFAULT_DURATION_H` | 24 h | 带宽 `DEFAULT_BANDWIDTH_HZ` | 30 MHz |
| 最小仰角 `DEFAULT_EL_MIN_DEG` | 10° | EIRP `DEFAULT_EIRP_DBW` | 47 dBW |
| 功率门限 `DEFAULT_C_MIN_DBM` | −100 dBm | G/R `DEFAULT_G_R_DBI` | 3 dBi |
| H3 分辨率 `DEFAULT_H3_RES` | 4 | 噪声温度 `DEFAULT_T_S_K` | 300 K |
| 默认区域 `DEFAULT_REGION` | 18,73,54,135 | 大气/极化/指向损耗 | 2 / 0.5 / 0.5 dB |

**性能取舍**：默认区域取中国中部框、H3 分辨率 4、24 h / 15 s，可在分钟级完成。放大地图或提高分辨率会让网格数与计算量近似平方增长，创建任务前请留意。

**可复现**：全部为确定性计算，同一组输入得到同一组结果；响应中附带传播 / 仰角 / 功率 / 聚合四个阶段的耗时，便于定位瓶颈。

---

## API 速查

共 17 个端点，完整定义见 `backend/app/main.py`；服务启动后可用 `http://127.0.0.1:8080/docs` 查看 Swagger UI。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查，返回状态与服务器时间 |
| GET | `/api/config` | 全局配置（时间倍率、仿真默认参数、时区） |
| GET | `/api/constellations` | 星座列表 |
| GET | `/api/constellations/{cid}/shells` | 壳层列表 |
| GET | `/api/constellations/{cid}/satellites` | 卫星列表（`only_default=true` 仅稳定壳层；`shell_ids=1,2` 按壳层筛选） |
| GET | `/api/constellations/{cid}/propagate?t=<ISO8601>` | 指定时刻的 ECI / ECEF 与星下点 |
| GET | `/api/satellites/{norad_id}` | 单星详情 |
| POST | `/api/constellations/{cid}/regenerate` | 用新的 Walker 参数重生成合成星座 |
| POST | `/api/simulations` | 创建覆盖仿真任务 |
| GET | `/api/simulations` | 任务列表（含状态、进度） |
| GET | `/api/simulations/{tid}` | 任务详情 |
| DELETE | `/api/simulations/{tid}` | 删除任务 |
| GET | `/api/simulations/{tid}/summary` | 汇总指标 |
| GET | `/api/simulations/{tid}/frames` | 覆盖帧时间步 |
| GET | `/api/simulations/{tid}/frame/{time_step}` | 指定帧的 H3 覆盖样本 |
| POST | `/api/admin/fetch/celestrak` | 手动触发一次 celestrak 拉取 |
| POST | `/api/spacetrack/query` | space-track 历史星历查询（凭据由前端传入） |

任务状态机：`pending → running → succeeded | failed | cancelled`，附带进度百分比、错误信息与分阶段耗时。

**创建任务示例**

```bash
curl -X POST http://127.0.0.1:8080/api/simulations \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "千帆-中国中部-24h",
    "constellation_id": "qianfan",
    "rule_type": "simple_elevation",
    "duration_h": 24,
    "sample_interval_s": 15,
    "h3_res": 4,
    "region": [28, 105, 42, 122],
    "use_default_shells": true,
    "params": { "el_min_deg": 10 }
  }'
```

字段约束：`duration_h ∈ [1, 72]`；`region` 为 `[lat_min, lon_min, lat_max, lon_max]`，缺省用 `DEFAULT_REGION`；`start_utc` 缺省为当天 00:00 UTC；`rule_type` 取 `simple_elevation` 或 `complex_power`。

---

## 配置项

复制 `.env.example` 为 `.env` 按需修改 —— 所有变量都有默认值，可整份留空。

| 分组 | 变量 | 默认值 |
|---|---|---|
| 服务 | `HOST` / `PORT` | `0.0.0.0` / `8080` |
| 存储 | `DATA_DIR` / `SQLITE_PATH` | `backend/data` / 其上 `constellation.db` |
| celestrak | `CELESTRAK_ENABLED` | `false` |
| celestrak | `CELESTRAK_FETCH_INTERVAL` / `CELESTRAK_TIMEOUT` | `7200` s / `20` s |
| 仿真 | `DEFAULT_*` 系列 | 见上一节参数表 |

---

## 测试

**后端计算引擎**（无网络依赖，4 个用例，覆盖传播形状、覆盖仿真、坐标往返、平近点角换算）

```bash
cd backend && ./venv/bin/python -m pytest -v
```

**前端端到端**（5 个用例：页面加载与地球渲染、星座切换与壳层筛选、时间轴实时按钮、创建仿真并查看结果、删除任务与历史回看）

```bash
cd frontend && npx playwright test
```

> ⚠️ 端到端用例当前有两个前置条件，直接跑会失败：
> 1. `playwright.config.ts` 的 `webServer.command` 硬编码了容器内路径 `/workspace/backend`，需要改成本机路径；
> 2. `baseURL` 指向 `http://127.0.0.1:8080`，因此必须先 `npm run build`，再让后端以单端口模式托管 `frontend/dist`。

---

## 常见问题

**`./venv/bin/uvicorn: No such file or directory`**
venv 没建，或没建在 `backend/venv`。见[快速开始第 2 步](#2-安装后端依赖)。

**`scripts/dev/start.sh` 起不来，前端 502 / 代理报错**
先确认 `frontend/node_modules` 存在（开发脚本不会自动 `npm install`），再看 `/tmp/csp_backend.log`。

**8080 / 5173 端口被占用**
改 `.env` 的 `PORT`，或先执行对应的 `stop.sh`（脚本内含 `pkill -f uvicorn` 兜底清理）。

**地球白屏 / WebGL 报错**
Cesium 需要 WebGL。远程桌面、虚拟机或纯软件渲染环境容易失败；Playwright 用例为此加了 `--use-gl=swiftshader` 参数，浏览器端可尝试开启硬件加速。

**celestrak 拉取失败**
预期行为。默认 `CELESTRAK_ENABLED=false`，网络不可达时使用基于真实星座设计参数的合成轨道根数，平台功能不受影响。

**space-track 查询报错**
需要用户凭据（前端弹窗输入）。缺失凭据或触发限流会给出明确提示，不会让服务崩溃。

**数据库想重置**
删掉 `backend/data/constellation.db` 后重启，会重新建表并写入种子星座。

---

## 数据与降级策略

| 数据源 | 正常路径 | 降级路径 |
|---|---|---|
| celestrak | 按 `CELESTRAK_FETCH_INTERVAL` 周期拉取并持久化真实 TLE | 网络不可达时跳过，使用合成轨道根数（`source=synthetic-fallback`），无阻塞、无报错中断 |
| space-track | 用户提供凭据后按需查询历史星历 | 缺凭据 / 限流时返回明确错误信息，前端展示提示 |
| 数据库 | SQLite 本地文件 | 首次启动自动建表 + 种子数据，无需手工迁移 |

---

## 已知限制与后续计划

- 未提供 CI、Docker / Compose 与发布流程；部署依赖 `scripts/` 与手动步骤。
- 端到端测试的 `webServer` 路径硬编码（见[测试](#测试)），需要按环境调整。
- `scripts/*.sh` 使用 POSIX 路径，Windows 下需手动启动或改用 WSL。
- 轨道模型为 J2 开普勒，未包含大气阻力、高阶引力场等长期摄动。
- 尚未声明开源许可证。

---

## 许可

本仓库暂未包含 `LICENSE` 文件。在补充许可证之前，默认保留所有权利；如需复用请先联系作者。

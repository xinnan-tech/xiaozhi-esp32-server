# 测试基础设施设计

**日期:** 2026-09-02
**状态:** 待审阅
**作者:** Claude（基于 spike 调研）

## 背景与目标

`xiaozhi-esp32-server` 是一个三语言项目：

- **Python** (`main/xiaozhi-server/`) — AI 核心服务（websocket + LLM/ASR/TTS 编排）
- **Java** (`main/manager-api/`) — 管理后台 API（Spring Boot + MyBatis-Plus）
- **Vue** (`main/manager-web/`) — 管理后台前端（Vue 2.6 + Element UI）

当前测试状态：

| 语言 | 源码 | 测试 | 覆盖率 | CI |
|---|---|---|---|---|
| Python | ~5,600 LOC | 0 | 0% | ❌ |
| Java | 316 文件 | 20 文件 | ~6% | ❌ |
| Vue | 36 组件 | 3 契约 | 极薄 | ❌ |

`main/xiaozhi-server` 是核心 AI 服务但零覆盖；Java/Vue 有测试但没接 CI（"写了不跑"比没写更糟）。

**目标：**
1. PR 推送时自动跑测试，所有现有测试不再"沉睡"。
2. Python 核心模块补单元测试，达到 ~25% 覆盖率（按 LOC）。
3. 三语言测试在本地用同一命令（`make test`）就能跑，结果与 CI 一致。
4. 不引入 e2e（项目尚未稳定到值得 5–10 分钟跑一个 e2e 的程度）。

## 非目标（明确不做）

- ❌ E2E 测试（Playwright/Cypress）—— 等 API 契约稳定后再评估
- ❌ manager-mobile（uniapp）测试栈 —— ROI 太低，另开议题
- ❌ 覆盖率门禁（如 `coverage < 80%` 阻断 PR）—— 避免逼人写假测试
- ❌ 重写现有测试 —— 增量改造
- ❌ 把 `node --test` 强迁到 vitest 之外另搞一套

## 总体架构

新增一个统一入口 `Makefile`（仓库根），把三语言测试命令收口：

```makefile
.PHONY: test test-python test-java test-web test-fast test-all

test: test-fast              # 默认：跑快的那一档（< 2 min）
test-all: test-python test-java test-web test-e2e   # 完整：含 e2e（将来）

test-fast: test-python test-java test-web
test-python:
	cd main/xiaozhi-server && pytest -x -q
test-java:
	cd main/manager-api && mvn -B -q test
test-web:
	cd main/manager-web && npm ci --no-audit --no-fund && npm run test:unit
```

CI workflow 直接调 `make test-fast`，跟本地等价。

## 切片设计

按 ROI 排序，每一刀独立可验收。

### Slice 1：CI 接通现有测试（本周，0.5–1 天）

**目标：** 让 Java 和 Vue 的现有测试在 GitHub Actions 上跑起来。

**新增文件：** `.github/workflows/test.yml`

```yaml
name: Tests
on:
  push:
    branches: [main]
  pull_request:
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.10', cache: 'pip', cache-dependency-path: 'main/xiaozhi-server/requirements.txt'}
      - run: |
          cd main/xiaozhi-server
          pip install -r requirements.txt pytest pytest-asyncio freezegun
          # Slice 1: smoke test only — Slice 2 才会补真正的测试
          pytest tests/test_smoke.py -x -q || pytest -x -q
  java:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: {distribution: 'temurin', java-version: '21', cache: 'maven'}
      - run: cd main/manager-api && mvn -B -q test
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '20', cache: 'npm', cache-dependency-path: 'main/manager-web/package-lock.json'}
      - run: cd main/manager-web && npm ci && npm run test:unit
```

**Python job 这一步是空跑**（占位，slice 2 才补测试）。显式 `|| echo "No tests yet"` 让它通过。

**验收：** PR 触发后，三个 job 都跑过，Java/Vue 的现有测试覆盖率体现在 CI 历史里。

### Slice 2：Python 核心模块单元测试（1–2 天）

**目标：** 覆盖第一档可测模块，~30–50 个测试。

**新增文件：**
```
main/xiaozhi-server/
├── pyproject.toml          # pytest 配置 + 包发现
├── pytest.ini              # 或合并到 pyproject.toml
└── tests/
    ├── __init__.py
    ├── conftest.py         # sys.path 处理 + 公共 fixture
    ├── core/
    │   └── utils/
    │       ├── test_textUtils.py
    │       ├── test_dialogue.py
    │       ├── test_output_counter.py
    │       ├── test_current_time.py
    │       ├── test_intent.py
    │       ├── test_llm.py
    │       └── test_memory.py
    ├── config/
    │   └── test_config_loader.py    # merge_configs
    └── plugins_func/
        └── test_loadplugins.py
```

**覆盖模块（按优先级）：**
1. `core/utils/textUtils.py` — emoji/标点处理
2. `core/utils/output_counter.py` — 每日字数计数
3. `core/utils/current_time.py` — 时间格式化（`freezegun` 跨日测试）
4. `config/config_loader.py::merge_configs` — 递归合并
5. `core/utils/dialogue.py::Message/Dialogue` — `pytest-asyncio` 测 `get_llm_dialogue_with_memory`，需要 mock `datetime.now()`
6. `core/utils/intent.py`、`llm.py`、`memory.py` — 小模块，附带覆盖
7. `plugins_func/loadplugins.py::auto_import_modules` — 包内模块遍历

**关键技术点：**

`xiaozhi-server` 的模块用 `from core.xxx import yyy` 这种**隐式相对导入**，所以 `conftest.py` 必须：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

**验收：** `pytest` 跑通 30+ 测试，覆盖率 ≥ 25%（LOC）。

### Slice 3：Java 单元测试扩展（2–3 天）

**目标：** 补 Java 关键业务模块的测试。

**策略：**
- 优先补 service 层（用 Mockito mock DAO），不引入 `@SpringBootTest`，跟现有 20 个测试风格保持一致
- 不动现有 20 个测试
- 给 `mvn test` 加 `-DfailIfNoTests=false` 避免空目录报错

**优先模块：**
1. `modules/correctword/service/impl/*ServiceImpl.java`
2. `modules/knowledge/service/impl/*ServiceImpl.java`
3. `modules/voiceclone/service/impl/*ServiceImpl.java`
4. `common/utils/` 下还没测的工具类

**验收：** Java 测试从 20 个增至 ~50 个，`mvn test` 仍 < 60 秒。

### Slice 4：Vue 迁移到 vitest + 组件测试（2–3 天）

**目标：** 从 `node --test` 契约测试升级到 vitest，能测 Vue 组件。

**变更：**
- `main/manager-web/package.json` 加 `vitest`、`@vue/test-utils@1`、`jsdom`（vitest 默认支持 jsdom 环境，不需要 Jest 插件）
- `npm run test:unit` 改为 `vitest run`
- 把现有 3 个契约测试保留（它们很有价值），扩展为可执行测试
- 新增组件测试优先级：
  1. `src/utils/featureManager.js` — 业务逻辑
  2. `src/utils/deviceTime.mjs`（已测，可转为真正的单元测试）
  3. `src/utils/format.js`、`date.js`
  4. `src/store/index.js` — Vuex mutations/actions

**验收：** `npm run test:unit` 跑通 10+ 测试，包含 1–2 个组件测试。

## 关键技术决策

| 决策 | 选择 | 理由 |
|---|---|---|
| Python 框架 | `pytest` + `pytest-asyncio` + `freezegun` | 社区标准，异步/时间测试刚需 |
| Python 包发现 | `conftest.py` 配 `sys.path` | 不动 `requirements.txt`，避免污染运行时 |
| Vue 框架 | vitest | Vue 2 兼容 `@vue/test-utils@1`，比 Mocha/Jest 配 webpack 简单 |
| CI runner | `ubuntu-latest` | 与现有 docker workflow 一致 |
| CI 缓存 | pip / Maven / npm 全部缓存 | 关键，否则 CI 慢到没人愿意等 |
| 测试入口 | 根 `Makefile` | 一行 `make test` 跟 CI 等价 |
| 测试分层 | 单测为主（不引入 e2e） | 项目尚未稳定 |

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| Java Spring 上下文启动慢（30s+）导致 CI 超时 | 切片 3 不引入 `@SpringBootTest`；只测纯逻辑 + Mockito mock service/dao，与现有 20 个测试风格一致 |
| Vue 测试需要 jsdom | vitest 默认带，无需额外配置 |
| Python 模块隐式相对导入在 CI 上跑不出 | conftest.py 的 sys.path 是唯一解；写一个 smoke test 在 CI 上验证模块能 import |
| 三语言测试互相等待 | 用 GitHub Actions job 矩阵，**并行**跑（不要 `needs:`） |
| 缓存键漂移导致 CI 不命中 | 用 `hashFiles()` 自动锁键 |

## 验收标准（全局）

完成所有切片后：

1. ✅ 任何 PR 推送后，GitHub Actions 自动跑三语言测试，全部通过
2. ✅ Python 单测覆盖率 ≥ 25%（LOC）
3. ✅ Java 测试从 20 增至 ≥ 50
4. ✅ Vue 测试从 3 增至 ≥ 10
5. ✅ `make test` 在本地一键跑，CI 跟本地结果一致
6. ✅ 所有测试总耗时 < 5 分钟（PR 反馈不能让人等太久）

## 实施顺序与时间估算

| 切片 | 时间 | 依赖 |
|---|---|---|
| 1. CI 接通 | 0.5–1 天 | 无 |
| 2. Python 单元测试 | 1–2 天 | 切片 1（CI 跑通 pytest 链路） |
| 3. Java 扩展 | 2–3 天 | 切片 1 |
| 4. Vue vitest | 2–3 天 | 切片 1 |

切片 2/3/4 可以并行（不同人/不同分支），但都依赖切片 1 先验证 CI 管道可用。

## 后续（不在本次范围）

- E2E（Playwright）：等 API 契约稳定后另起议题
- manager-mobile（uniapp）测试：单独评估
- 覆盖率门禁：在覆盖率达到 ~50% 后再考虑
- 性能基准：`main/xiaozhi-server/performance_tester.py` 可视化、回归检测
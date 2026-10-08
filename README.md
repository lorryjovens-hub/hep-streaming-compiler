# HEP Streaming Compiler · LAAP 原生流式 GUI 编译器

> **对话用来造，界面用来用。**
> Conversations build; interfaces serve.

[![tests](https://img.shields.io/badge/tests-32%20passed-brightgreen.svg)](tests)

GPT-6 的 Intelligent UI 靠三件套：**原子组件库 · 流式编译器 · 审美判断层**。
本项目是 LAAP 的同构实现，长在 HEP（HarnessComposer / intent_mapper）的根上。

## 为什么不是"生成 HTML"

| 旧世界（Artifacts / iframe） | 新世界（编译式组件） |
|---|---|
| 模型写整段 HTML/JS，冷启动 | 组件是**编译目标**，预封装、类型化 |
| 全量生成完才能渲染 | **流式编译**：token 进来一帧长一帧 |
| 风格割裂、AI 垃圾审美 | 设计纪律**编译期内建**（审美 lint） |
| 界面答完即弃 | 编译产物可挂卡片/工作台长期使用 |

## 架构

```
LLM token 流
   │  SpecParser（增量围栏解析，容错不完整行）
   ▼
spec ops（JSONL：create / patch / remove）
   │  lint（DEV_CHARTER / HEP 规则：Lucide 禁 emoji、label 必填、禁 alert…）
   ▼
组件编译（12 型原子件：heading/text/button/input/slider/stat/
          progress/checklist/card/chart/note/divider）
   ▼
RenderOps 流（append / patch / remove / lint）──▶ 宿主
   ├─ Hana 卡片（card:request/response 协议）
   ├─ Showcard / 工作台（取到黑板长期使用）
   └─ 普通浏览器（runtime/hep-runtime.js 逐帧挂载）
```

## HEP-Stream Spec v0（协议）

模型在回复中流式输出 ` ```hep ` 围栏，每行一个完整 JSON op：

```jsonc
{"op":"create","id":"s1","type":"slider","props":{"label":"人数","min":2,"max":12,"value":4,"bind":"guests"}}
{"op":"patch","id":"st1","props":{"value":"3.2 kg"}}
{"op":"remove","id":"tmp1"}
```

**行完成即编译**——无需等整段，天然抗 token 截断（flush 兜底）。

## 快速上手

```python
from hep_stream import HEPCompiler

c = HEPCompiler()          # strict=True 时 error 级 lint 违规阻断编译
for chunk in llm_token_stream:        # 真实场景：LLM 流
    for op in c.feed(chunk):          # 逐帧拿到 RenderOps
        host.apply(op)                # 卡片/浏览器逐帧生长
c.flush()
```

浏览器端：`runtime/hep-runtime.js` 提供 `HEP.attach(container)` +
`HEP.apply(ops)`，交互件输入经 `bind` 字段回传（`HEP.inputs`）。

跑演示：

```bash
python examples/demo_dinner.py       # 烤羊腿计划：6 帧流式生长
python -m pytest tests/ -q           # 32 tests
```

## 设计纪律（编译期 lint）

| 规则 | 级别 | 内容 |
|---|---|---|
| L1 | error | icon 必须 Lucide 名（HEP 规则：禁 emoji 图标） |
| L2 | warn | 字符串禁 emoji 字符 |
| L3 | error | 禁 alert( |
| L4 | warn | 裸色值 → 用设计 token |
| L5 | error | 交互件必须有 label（可访问性） |
| L6 | warn | 禁 font-weight:700 |

## 与 A2UI 的关系

Google 的 A2UI（Agent-to-UI 协议）与本项目同题。对齐计划见
`docs/A2UI-ALIGNMENT.md`（调研进行中）：组件模型、能力协商、
增量更新语义三处直接相关，本 spec 保持可映射结构。

## 目录

```
hep_stream/   components.py（原子组件）· parser.py（增量解析）
              lint.py（审美纪律）· compiler.py（流式编译器）
runtime/      hep-runtime.js（浏览器端逐帧挂载）
tests/        14 tests：增量性 / 容错 / lint / 编译
examples/     demo_dinner.py（流式生长演示）
```

## v0.3 · HEP 学习引擎（设计馆原子化生成）

设计馆 383 个组件块（10 设计源）向量化为 **512 维设计原子**，在高维空间做组合运算：

```python
from hep_stream.learning import build_corpus, Composer

index = build_corpus()          # 383 原子 / 0.2s
c = Composer(index)
arr = c.arrange("AI 音乐订阅支付结算页", layout="hero-stats-form")
c.refine(arr, towards="pricing table", away="hero banner", slot_index=0)
for op in arr.stream():          # 流式 spec ops
    ...
```

运算层（vecspace）：compose（加权质心）· blend（风格渐变）· contrast（排斥性微调）·
nearest（最近邻）。排布器把「意图 × 布局原型」在向量空间合成槽位查询点，
用互斥最近邻填充设计馆原子——**原子化生成排布，天然流式**。

## A2UI 对齐与开源

- catalog 契约（能力协商 / 校验 / 消息映射）见 `docs/A2UI-ALIGNMENT.md`
- 官方渲染器实测：`@a2ui/react` / `@a2ui/lit`（npm 0.12.0）；Flutter GenUI 需 SDK
- 设计馆语料：10 设计源 383 块 + 4 图标集（lucide-static 优先）

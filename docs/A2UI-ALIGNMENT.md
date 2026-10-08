# A2UI 对齐说明 · HEP-Stream v0 → v1

> 基于 2026-10-08 对 a2ui-project/a2ui（Google，Apache 2.0，v0.9.1 公测）
> 的调研。官方：https://a2ui.org/ ｜ https://github.com/a2ui-project/a2ui

## 一、A2UI 是什么

Agent 跨信任边界发送**声明式 UI** 的开放协议："safe like data, expressive
like code"——不发可执行代码，发组件描述，由客户端用自有原生控件渲染。
与 A2A（agent↔agent）、MCP（agent↔工具）正交；是 Artifacts/iframe 路线的
替代品。核心模型：**Surface + Catalog（JSON Schema 组件目录）+ 组件 +
数据模型（JSON state）**。

## 二、我们已天然对齐的部分（v0 就做对了）

| A2UI 设计 | HEP-Stream v0 现状 | 判定 |
|---|---|---|
| JSONL 流式消息序列 | ` ```hep ` 围栏内每行一个 JSON op | ✅ 同构 |
| 组件 ID 级 upsert（updateComponents） | `op: create/patch/remove`，patch 即按 id upsert | ✅ 同构 |
| 扁平邻接表（parent/children 引用） | spec 带 `parent` 字段，非嵌套树 | ✅ 同构 |
| 渐进渲染（边生成边渲染） | feed() 逐帧产 RenderOps | ✅ 同构 |
| 组件目录约束 | REGISTRY + required/optional props 校验 | 🟡 需升级为 catalog 契约 |

## 三、v1 对齐计划（按优先级）

1. **Catalog 契约化**：REGISTRY 导出 JSON Schema（组件/属性/组合约束
   allowedParents），支持 `supportedCatalogIds` 能力协商；窄 catalog =
   降级公共子集（对应 A2UI Basic Catalog 思路）。
2. **结构/状态分离**：spec 拆两路——组件定义（结构）+ 数据模型（state）；
   新 op `{"op":"data","path":"/guests","value":4}` 走 JSON Pointer
   (RFC 6901) 路径级更新；组件 `bind` 升级为指针双向绑定。
3. **消息协议对齐**：消息带 `version` 与 `surfaceId`；create/update/delete
   语义命名对齐 A2UI；16ms 批量 + diff（A2UI 性能建议）。
4. **交互建模**：`action.event{name, context}` 模式（命名动作 + 上下文
   路径回传），预留 RPC（`allowedCallers` 权限面）。
5. **双轨渲染**：保留 Hana 卡片/Showcard 作为宿主；并评估**直接输出 A2UI
   surface 消息**，换取官方 React/Flutter/Compose 渲染器（移动端免费午餐）。

## 四、战略判断

A2UI 证明了"编译式组件 + 流式"是行业共识方向；我们的差异化在于：
**审美 lint 内建**（A2UI 只管合法，不管好看）、**与记忆系统同构**
（界面为项目和关系生长，不只为任务）、**Hana 卡片即预埋渲染层**
（A2UI 需要客户端集成渲染器，我们的宿主天生就有）。
结论：**做 A2UI 的超集，不做它的仿品**——协议层兼容，判断层自主。

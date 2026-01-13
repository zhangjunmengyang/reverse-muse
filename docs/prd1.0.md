既然目标明确，要做一个**极简、高智能、主动式**的 MVP，我们不需要更多的确认了。直接进入执行模式。

这是一份可直接交付给开发团队（或用于你自己开发）的 **PRD (产品需求文档)**。

---

# Project: Reverse Muse (MVP)
**版本号**：v0.1.0
**核心理念**：AI 不是被动问答的工具，而是阅读时的“第二大脑”。它通过气泡形态主动浮现，提供记忆链接和深度洞察。

## 1. 产品概览 (Product Overview)

### 1.1 用户场景 (User Story)
用户打开一个 PDF 论文进行阅读。界面极简，顶部有一个隐藏的区域。
*   当用户**划选**一段文字时，顶部气泡柔和展开，AI 提示：“这段逻辑跟前言里的假设是冲突的...”
*   当用户**长时间停留**在一个公式前，气泡展开：“还记得吗？这和你昨天看的 ResNet 里的残差块公式几乎一样。”
*   当用户**快速扫读**时，AI 保持静默，顶部无遮挡。

### 1.2 核心价值
*   **Zero Friction (零摩擦)**：不需要用户输入 Prompt。
*   **Proactive (主动性)**：AI 预判需求。
*   **Minimalist (极简)**：用完即走，不占空间。

---

## 2. 功能需求 (Functional Requirements)

### 2.1 界面与交互 (UI/UX)

#### 2.1.1 阅读器主体
*   **布局**：全屏阅读模式，左/中显示 PDF 内容（推荐单列滚动模式）。
*   **技术选型**：`react-pdf` (Web) 或 `PDF.js`。

#### 2.1.2 "Ghost Bubble" (灵动气泡)
这是产品的灵魂。
*   **位置**：屏幕顶部中央（类似 iOS 灵动岛，或者 macOS 的通知横幅，但更轻量）。
*   **默认状态**：**完全隐藏** (Opacity: 0) 或 **极小圆点** (表示 AI 在线)。
*   **激活状态**：
    *   **动画**：从无到有，高度自适应展开，背景半透明磨砂 (Glassmorphism)。
    *   **内容**：纯文本流式输出 (Streaming Text)。
    *   **操作**：气泡角落有一个极小的“展开详情”或“Pin住”按钮（MVP 可暂不做，仅展示文本）。
    *   **关闭逻辑**：
        *   用户继续滚动页面 -> 气泡自动收起。
        *   用户点击页面空白处 -> 气泡收起。
        *   5秒无交互 -> 气泡淡出。

### 2.2 触发机制与 AI 逻辑 (The Brain)

我们需要构建一个 **"Observer Loop" (观察者循环)**，后端逻辑如下：

#### A. 显性触发 (Explicit Trigger) - 优先级高
*   **动作**：用户划词 (Selection)。
*   **逻辑**：
    1.  前端捕获划选文本 `Selection_Text`。
    2.  发送给 LLM。
    3.  **Prompt 策略**：不只是解释，而是寻找“Insight”或“Contradiction”。
    4.  **UI 响应**：气泡立即弹出。

#### B. 隐性触发 (Implicit Trigger) - 优先级中
*   **动作**：用户在某视口 (Viewport) 停留超过 `T=5s` 且鼠标有微动（排除了人走开的情况）。
*   **逻辑**：
    1.  获取当前视口中心的文本块 `Focus_Text`。
    2.  **RAG 检索**：去向量库搜索用户以前读过的文章。
    3.  **判别器 (Discriminator)**：让一个小模型（或 Prompt）判断——“这里有值得说的话吗？比如和旧知识的联系？”
    4.  **结果**：
        *   如果有 (Confidence > 0.8) -> 气泡弹出：“这让你想起了 xxx 吗？”
        *   如果没有 -> 保持静默 (Silence)。

#### C. 记忆链接 (Memory Linking) - 核心差异化
*   **数据录入**：
    *   用户上传 PDF 时，后台自动分块 (Chunking) 并存入向量数据库 (Vector DB)。
*   **检索逻辑**：
    *   每次触发 A 或 B 时，不仅看当前文，还要检索 Vector DB 中 **“非本文”** 的高相似片段。
    *   如果检索到高分匹配（Similarity > 0.85），强制 AI 在输出中提及：“这和你在《[Paper Title]》里读到的 xxx 很像。”

---

## 3. 技术架构方案 (Technical Architecture)

### 3.1 技术栈 (Stack)
*   **Frontend**: Next.js (React) + Tailwind CSS (UI) + Framer Motion (气泡动画必备).
*   **Backend**: Next.js API Routes (Serverless) 或 Python FastAPI.
*   **LLM**: OpenAI GPT-4o (主脑) + GPT-3.5-turbo/Claude-Haiku (用于快速判断是否需要静默).
*   **Vector DB**: Pinecone (云端，快速集成) 或 Chroma (本地化).

### 3.2 数据流 (Data Flow)

1.  **Input**: 用户行为 (Scroll position, Selection, Hover duration).
2.  **Middleware (The Gatekeeper)**:
    *   前端防抖 (Debounce)：防止滚动时疯狂触发请求。
    *   如果用户正在快速滚动，**挂起所有 AI 请求**。
    *   只有状态稳定 (Stable) 后，才发送 Context 到后端。
3.  **Backend Processing**:
    *   `Context` + `History (RAG)` -> `LLM`
4.  **Output**:
    *   如果是 `[SILENCE]` -> 前端不渲染气泡。
    *   如果是 `[TEXT]` -> 前端气泡展开，流式打字机效果显示。

---

## 4. MVP 阶段Prompt 设计 (System Prompt)

这是实现“像人一样思考”的关键。

```markdown
Role: You are an intellectual reading companion using "Theory of Mind". You are NOT a search engine. You are a "Reverse Muse".

Context: The user is reading a paper.
Current Text: "{current_text_chunk}"
User Action: "{highlighted OR lingered}"
Related Memory (RAG): "{retrieved_segment_from_past_paper}"

Instructions:
1. Analyze the Current Text.
2. If User Action is "lingered", guess WHY they stopped. Is it complex? Is it a brilliant insight? Is it controversial?
3. Check the Related Memory. If it's highly relevant, YOU MUST connect them. (e.g., "This contradicts what you read in X...")
4. Output format:
   - If nothing interesting to add, output simply: [SILENCE]
   - If you have an insight, output a concise, conversational thought (max 1 sentence). DO NOT act like a robot. Be like a smart colleague whispering a hint.

Tone: Insightful, Brief, Low-friction.
```

---

## 5. 开发里程碑 (Milestones)

*   **Week 1: 骨架搭建**
    *   完成 PDF 渲染器。
    *   实现顶部的“气泡”组件（动画效果：隐藏 -> 展开）。
    *   打通 OpenAI API，实现最简单的“划词 -> 气泡显示翻译/解释”。

*   **Week 2: 记忆与感知**
    *   接入 Pinecone。
    *   实现“文件上传 -> 向量化”流程。
    *   实现“停留监测”逻辑（防抖 + 计时器）。
    *   调试 Prompt，让 AI 学会闭嘴（输出 `[SILENCE]`）。

*   **Week 3: 体验打磨 (The "Magic")**
    *   **流式输出优化**：气泡内的文字不能一次蹦出来，要像思维产生一样流出来。
    *   **关联度微调**：调整 RAG 阈值，确保 AI 说的“你以前看过”是准确的。

---

### 给开发者的执行建议 (Actionable Advice)

1.  **不要一开始就做复杂的眼动追踪**：用“鼠标停留位置”+“页面滚动停止”作为注意力的代理指标，准确率足够 MVP 使用。
2.  **气泡的物理质感很重要**：这个 MVP 唯一的 UI 就是那个气泡。用 `Framer Motion` 把它做得丝般顺滑（Spring physics），这决定了用户是觉得它是“广告弹窗”还是“智能伙伴”。
3.  **Cost Control**：停留触发可能会消耗大量 Token。务必在 Prompt 头部加指令：`Check if content is trivial first. If trivial, return [SILENCE] immediately.` 这样可以省钱并减少打扰。

这就是你要的 PRD。如果没问题，我们可以开始写代码了。
# ManiScope 用户手册

## ManiScope 是什么

ManiScope 是一个用于评估加密货币市场交易型价格操纵风险的可视化分析仪表板。当前前端聚焦于去中心化交易所中的 memecoin 活动，并内置 ACT 和 PNUT 两个 Solana 代币数据集。系统会加载预先计算好的交易日志、转账日志、按小时粒度的余额快照，以及每个用户的行为序列，然后在这些数据之上运行实体检测、链接检测和操纵检测。

ManiScope 更适合作为调查员的分析工作台，而不是实时监控系统。它帮助回答的问题包括“在观察期内谁在操纵这枚代币”“哪些钱包看起来存在关联”“可疑活动如何与价格变化对齐”。典型工作流是探索式的：选择代币和快照，检查分布视图和操纵视图，选择用户或操纵卡片，标注证据，并在调查结果准备好共享时导出会话。

## 屏幕布局

仪表板会铺满浏览器窗口。当前 UI 在顶部标题栏下方分成三列。

```
+---------------------------------------------------------------------------------------------+
| ManiScope | Session | Human Workspace | Analysis Import | Codex Chat | Coin: ACT PNUT | Study Info Export Import |
+------------------+------------------------------+------------------------------+
| Control Panel    | Token Distribution           | ACT or PNUT K-Line           |
|                  |                              | round-trip cards             |
| Snapshot         | top-holder graph             | candlestick chart            |
| Entity           | entity circles and links     | same-direction cards         |
| Manipulation     +------------------------------+------------------------------+
| Link             | User Actions | Annotations   | Behavior Details             |
|                  | Action Tree                 | selected user or card users  |
+------------------+------------------------------+------------------------------+
```

标题栏包含产品名、会话标记、工作区标记、`Analysis Import` 标签、Codex Chat 按钮、ACT 和 PNUT 单选按钮，以及 `Study Info` / `Export` / `Import` 控件。

左列是 Control Panel。中列上方是 Token Distribution 视图，下方是带标签页的调查面板。右列上方是 K 线和操纵卡片视图，下方是 Behavior Details。

## Human 和 Agent 工作区

每个 ManiScope 浏览器页面都属于一个工作区角色。

- `/{sessionId}/human` 是 Human Workspace。它是用户交互、标注、导入 trace、重排 trace 项目和用户笔记的权威来源。
- `/{sessionId}/agent` 是 Agent Workspace。它是 Codex 或另一位分析者使用的独立可视分析页面，可以探索同一个会话，但不会改变人的页面状态。
- `/{sessionId}` 仍然有效，并会打开 Human Workspace。访问 `/` 会创建一个新的 5 字符会话并跳转到 Human Workspace。

两个工作区都会读取会话中共享的 canonical trace。当你在人的页面交互、标注、导入、重排或同步会话时，Human Workspace 会写入 canonical trace。Agent Workspace 会在后台刷新这份 canonical trace，因此它可以看到人已经做过什么，但智能体侧的选择、检测器设置、缩放窗口、选中用户和渲染证据会单独保存。在 Agent Workspace 中，Action Tree 是只读的。

为了保持向后兼容，`current-state.json` 仍表示人的当前状态。同时，human 和 agent 会分别维护 `workspaces/human/current-state.json` 和 `workspaces/agent/current-state.json`。这意味着智能体可以运行不同的检测参数、查看不同快照、选择不同用户或渲染证据图片，而不会覆盖人的可见分析状态。

## Baseline 会话

Baseline 会话用于评估通用 Codex 助手与专门的 ManiScope 智能体之间的差异。

- 访问 `/base` 会创建一个新的 5 字符 baseline 会话，并跳转到 `/base/{sessionId}`。
- `/base/{sessionId}` 会恢复对应的 baseline 会话。
- `/base/{sessionId}/agent` 不提供独立工作区，会跳回 `/base/{sessionId}`。

Baseline 会话使用独立的存储根目录：`.maniscope-chat/baseline-sessions/{sessionId}`。它仍然会记录用户动作、标注、导入内容、截图、当前状态、聊天历史和 artifacts，但聊天提示词会刻意保持通用。Baseline 智能体可以查看原始数据、trace 文件、截图和当前状态，但不会获得专门的 reasoning-graph 方法、trace-analysis 工具、skeptical-review skill、Agent Workspace 或可任意重渲染可视化的 helper。

如果 baseline 智能体需要当前视图图片，会话中包含 `maniscope_baseline_views.py`。这个 helper 只能把最近同步的 Token Distribution、K-line 和 Behavior Details 截图复制到 `artifacts/`；它不能改变检测参数、选中用户、时间窗口、缩放比例、粒度或任何其他可视化状态。

specialized 和 baseline 聊天会话都会在会话根目录生成 `pyproject.toml`、`package.json` 和 `.gitignore`。这些文件用于会话本地脚本环境，智能体可以用 `uv` 运行 Python 脚本，也可以用 `bun` 运行 JavaScript 或 TypeScript 脚本，并在需要时添加临时分析依赖。持久证据和报告仍应保存到会话的 `artifacts/` 文件夹。

## Control Panel

Control Panel 驱动其他视图中的计算结果。它可以垂直滚动，当前按顺序包含四组配置：Snapshot Configuration、Entity Detection、Manipulation Detection 和 Link Configuration。

### Snapshot Configuration

Snapshot Configuration 控制其他视图使用的持有者群体。

- **Snapshot Time** 从当前代币数据集中选择一个整点时间戳。首次加载和切换代币后，应用会选择最新可用的快照时间。
- **Top Holders Threshold** 控制头部持有者集合需要覆盖的用户持币供应比例。默认值是 `0.3`。
- **Related User Threshold** 根据相对于最小头部持有者余额的比例筛选相关持有者。默认值是 `0.2`。
- **Update Snapshot** 会重新加载快照，并使用当前配置自动重跑实体检测、链接检测和操纵检测。

更新快照也会在 User Actions 和 Action Tree 标签页中记录一条系统动作。

### Entity Detection

Entity Detection 会把钱包聚类成更严格的钱包群组。Run Detection 按钮会更新实体分组；当基于实体的操纵检测处于启用状态时，它还会重跑操纵检测，使 K 线视图和 Behavior Details 与新的实体结果保持一致。

Entity Detection 包含三组可折叠规则。

- **Network Based** 可以作为规则族启用，内部包含 Direct Transfer、Min Tx Count、Min Volume、Funding Relationship、Same Sender 和 Same Recipient 控件。默认情况下规则族开关关闭，但该区块内部的 Direct Transfer、Min Tx Count 和 Funding Relationship 已经勾选。
- **Similarity Based** 默认启用。它包含 Trading Action Sequence、Balance Sequence 和 Earning Sequence 控件。Balance Sequence 默认启用，粒度为 1 小时，相似度为 `0.6`。
- **Manipulation Based** 可以根据被检测出的操纵行为在时间上的接近程度来聚合用户。它默认关闭，并提供 Max Time Diff 参数。

检测结果会在 Token Distribution 视图中显示为橙色虚线实体边界。当选择某个已聚类用户时，Behavior Details 中也会显示实体成员信息。

### Manipulation Detection

Manipulation Detection 会更新 K 线视图、Token Distribution 节点描边，以及 Behavior Details 操纵框中显示的可疑交易模式。

当前有两组规则。

- **Round Trip** 检测买入后卖出或卖出后买入的序列，要求净持仓回到接近起点，并且收益有限。默认参数是 Max Time Diff `120`、Max Position Diff `100`、Max Earning `1000`，并勾选 Enable Entity Based。
- **Same Direction** 检测连续同向动作。默认参数是 Max Time Diff `10`、Min Seq Length `5`、Max Diff Direction `0`，并勾选 Enable Entity Based。

基于实体的检测会先合并同一实体内钱包的交易，再运行操纵检测器。这可以揭示在单地址视角下较弱或不可见的协同行为。

### Link Configuration

Link Configuration 检测持有者之间更柔性的两两关系。它使用与 Entity Detection 类似的规则族，但目的更偏向探索。Update Links 会刷新 Token Distribution 视图中的灰色链接层。

当前 Link Configuration 的默认设置是：

- Network Based 关闭，Direct Transfer 可用，Min Tx Count 设置为 `1`。
- Similarity Based 开启，Trading Action Sequence 启用，匹配类型为 Action Only，Min Seq Length 为 `3`，Max Time Diff 为 `120`。
- Manipulation Based 开启，Max Time Diff 为 `120`。

当你需要更严格的分组时使用实体检测。当你需要更弱但可能有价值的关系线索时使用链接检测。

## Token Distribution View

Token Distribution 视图位于中列上方。它把当前快照显示为一个节点链接分布图。

标题栏显示快照时间、**Show Links** 开关、**Scale** 滑块、活跃用户数量，以及用于快照标注的相机按钮。

视觉编码如下：

- 头部持有者显示在主要圆形区域内。节点越大，代表代币余额越高。
- 当相关用户通过 Related User Threshold 筛选时，它们显示在头部持有者群体周围。
- 红色描边节点表示当前操纵规则结果中涉及的用户。
- 蓝色描边节点表示当前操纵结果没有标记该用户。
- 橙色虚线边界表示检测出的实体群组。
- 橙色虚线连接表示相关用户与某个实体邻域相连。
- 当 Link Configuration 发现两两关系且 Show Links 启用时，灰色链接会显示出来。

悬停节点会显示工具提示，内容包括地址、余额和可用的检测上下文。点击节点会选择该用户，并填充 Behavior Details。Scale 滑块可以改变图的缩放比例，不会重跑检测。

相机按钮会打开 Token Snapshot 标注对话框。该对话框会保留图形状态，并允许你选择节点、在视图上绘制草图、添加文字，然后把标注保存到 Annotations 和 Action Tree 标签页中。

## K-Line And Manipulation View

K 线视图位于右列上方。它把价格变化与检测出的操纵事件结合在一起。

标题栏包含当前代币标签、粒度按钮和相机按钮。当前粒度选项是 `1m`、`5m`、`15m`、`30m`、`1h`、`1d`、`3d` 和 `1w`。

中央图表显示 OHLC 蜡烛图。绿色蜡烛表示收盘价高于开盘价，红色蜡烛表示收盘价低于开盘价。视图还会显示淡蓝色连接带，把操纵卡片与图表中对应的时间区间连接起来。

操纵卡片围绕图表排列：

- 蜡烛图上方的卡片表示 Round Trip 事件。
- 蜡烛图下方的卡片表示 Same Direction 事件。
- 每张卡片显示时间槽、精确时间范围、约略美元金额，以及一个小型动作序列图形。
- 水平滚动条允许你独立滚动上下两行卡片。

点击操纵卡片会把参与用户加载到 Behavior Details，并以 “Card Users” 模式展示。若启用了悬停自动截图，长时间悬停卡片会记录一条 hover 动作。

K 线视图和 Behavior Details 可以同步时间窗口。当另一个视图存在可同步的时间窗口，并且当前模式允许同步时，会出现 Sync Time 按钮。当 Behavior Details 启用 Sequential Time 时，Behavior Details 中的同步按钮会被禁用，因为此时行为图不再使用相同的绝对时间尺度。

## Behavior Details View

Behavior Details 位于右列下方。在点击 Token Distribution 用户节点或操纵卡片之前，它默认为空。

当选择 Token Distribution 中的某个用户时，该面板会显示该用户和可用的相关用户。如果该用户属于某个实体，面板会显示实体标记和成员数量。当选择操纵卡片时，面板会切换为 Card Users 模式，并显示该卡片涉及的用户。

行为图结合了持有者活动的三个方面。

- 动作圆点沿时间线显示买入、卖出和转账。
- 余额根据行和缩放层级显示为面积或条形历史。
- 收益使用盈利和亏损条形显示。

该面板中的控件包括：

- **Show Related Users**，在检查单个选中用户时可用。
- **Sequential Time**，按事件顺序而不是绝对时间重新排列行为序列。
- **Show Manipulation Boxes**，当存在操纵结果时可用。
- **Sync Time**，当 K 线视图有兼容的选中时间窗口时可用。
- 用于 Behavior Snapshot 标注的相机按钮。

点击 Behavior Details 中的用户标签可以切换选中用户。缩放行为图会记录 zoom 动作，并且在对应动作类别启用时可能捕获视图快照。

## Codex Chat

浮动的 Codex Chat 侧边栏可以让你要求智能体检查当前会话 trace、解释交互路径、推荐调查步骤，或继续进行分析。每条消息发送前，ManiScope 会同步共享的实时 trace 和当前工作区状态。来自 Human Workspace 的消息会附带人的工作区截图；来自 Agent Workspace 的消息会附带智能体工作区截图。

聊天历史和生成的 artifacts 在会话层级共享。智能体提示词会区分三类上下文：共享的 canonical trace、人的当前状态，以及智能体私有的探索状态。智能体的可视探索应使用 Agent Workspace，并且不应追加到人的动作 trace，除非你明确要求生成持久 artifacts 或 reasoning patches。

Codex Chat 历史会在智能体流式输出时增量保存。如果你在长回合中刷新页面，或浏览器连接中断，已经收到的文本、活动更新和 artifact chip 会作为部分 transcript 重新加载，而不会消失。被中断的助手回合会标记为部分结果，已经生成的 artifact 仍然可以打开，因为它们保存在会话文件中。

在 baseline 会话中，Codex Chat 使用 `/api/base/chat/...`，文件存储在 `.maniscope-chat/baseline-sessions/{sessionId}`。聊天面板会标记为 `Baseline`，Agent Workspace 入口、分析快捷按钮和右侧面板的 LLM Analysis 标签页都会隐藏，提示词只描述价格操纵分析任务和可用原始数据，不包含专门的 trace-analysis 指令。

每个聊天会话根目录都包含用于临时脚本的项目模板：`pyproject.toml` 用于通过 `uv` 运行 Python，`package.json` 用于通过 `bun` 运行 JavaScript 或 TypeScript。智能体可以在该会话内添加依赖；生成的证据、报告和导出文件应放在 `artifacts/`。

Codex Chat 智能体会从当前会话目录运行，而不是从仓库根目录运行。它只能在该会话工作区内写入文件，优先写入 `artifacts/`；ACT 和 PNUT 原始数据目录会作为额外的只读策略输入提供。Python 依赖会使用仓库本地的 uv 缓存 `.maniscope-chat/shared-uv-cache`，bridge 会通过 Codex writable roots 授权该缓存目录，因此智能体可以直接使用 `uv`，不需要手动设置 `UV_CACHE_DIR`。网络访问保持开启，因此智能体可以访问本地 ManiScope 服务，并在调查需要时获取外部参考。bridge 启动时会检查本机是否已经安装 `uv`、`codex`，以及 `bun` 或 `npm` 中的一个。

Codex Chat 面板是浮动的。拖动标题栏可以移动面板，拖动底部两个角可以调整大小。面板的位置和大小会保存在当前浏览器中。

消息输入框上方的 **Run Full Analysis** 按钮会发送一个完整 trace-analysis 流程的预设请求。它要求 Codex 先写入并验证 `reasoning-graph.json`，在有用时使用只收集证据的 subagent 执行后续检查，由主智能体写入 graph patch，并在汇报前完成验证，最后用用户使用的语言给出面向人的解释摘要。

当 LLM Analysis 中已经有 `reasoning-graph.json` 后，**Update Analysis** 按钮会显示在 **Run Full Analysis** 右侧。它会发送增量分析 prompt，要求 Codex 对比最新 graph 或 patch anchor 与当前 live trace，只分析新增的交互和标注，在有新证据时写入 `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json`，验证 graph 与 patch，并同时给出技术审计和使用用户语言的面向人解释摘要。聊天历史中，这两个快捷请求会显示为简短标签，例如 `Run full analysis` 和 `Update analysis`，不会显示完整的隐藏 prompt 文本。

在智能体回合中，临时的 Thinking 面板可能会显示在助手回复上方，用来展示实时进度。持久的 Agent Activity 会按照流式事件到达顺序嵌入到回复正文中。连续的活动事件默认折叠成一个小卡片，只显示该序列中的最新活动；展开卡片后可以查看完整活动流，以及可用的命令输出。

助手回复可以包含 Markdown 文本、生成的 artifact、JSON 文件、Markdown 报告和图片预览。生成的 artifact chip 会出现在 ManiScope 收到它们的对应位置，因此你可以看到某个文件是在某条状态更新或解释之后创建的。当智能体在回复中提到本地图片、Markdown 或 JSON 路径时，如果该文件位于当前会话文件夹、项目文件夹，或显式允许的 artifact 根目录下，ManiScope 会通过会话 artifact 接口生成链接。有效图片会被复制到会话的 `artifacts/` 文件夹用于预览；Markdown 和 JSON 输出会显示为可下载的 artifact 链接。聊天中生成的文件通常应保存到会话 `artifacts/` 文件夹；需要长期保存的 trace 分析 artifact 则应保存到对应 trace 的 `analysis-results/` 文件夹。

对于可视化后续调查，每个会话还会包含一个托管的 Python helper：`maniscope_visualization.py`。智能体可以从会话文件夹导入它，通过隔离的 Agent Workspace 浏览器页面渲染 Token Distribution、K-line 和 Behavior Details 图片。bridge 会先等待 Agent Workspace 的可视化数据完成加载，再提取当前渲染参数。这些渲染结果会以 PNG 证据保存到共享的会话 `artifacts/` 文件夹，并且不会改变 Human Workspace 的状态。

对于完整的 trace 分析，每个会话还会包含一个托管的 skeptical-review skill。可用时，智能体可以派生一个聚焦的子智能体，专门寻找削弱主要假设的负面证据、误报、良性解释或模型参数不稳定性。主智能体需要先验证这些候选负面发现，然后才会把它们作为 `contradicts`、`refines` 或 Reasoning Gap 条目加入分析 artifact。

当已有分析结果存在，而你继续在界面里分析并产生新的 trace 时，智能体可以执行增量 trace 分析，而不是重新计算全部内容。ManiScope 会为每个实时 trace 版本保存 trace anchor，智能体会把它和 `reasoning-graph.json` 以及 patch 文件中的 anchor 对比。新证据会写入 `reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json`。如果 patch 文件累积较多，智能体可以先 materialize 出 `current-reasoning-graph.json` 作为完整图的阅读辅助；当活跃 patch 数达到 8 个时，可以 checkpoint 这组 patch。

## User Actions、Annotations、Action Tree 和 LLM Analysis

中列下方的面板现在是调查工作流的一部分。在 specialized 会话中，它包含四个标签页：User Actions、Annotations、Action Tree 和 LLM Analysis。在 baseline 会话中，LLM Analysis 标签页会隐藏。默认激活的标签页是 Action Tree。

### User Actions

User Actions 标签页会随着调查过程记录交互事件。示例包括快照更新、检测运行、代币切换、K 线粒度切换、用户选择、卡片点击、缩放、滚动和开关变化。

计数徽标显示当前记录了多少动作。每张动作卡片都可以展开以查看 JSON 细节和视图状态。当对应动作类别启用了快照捕获时，卡片还会显示 source 和 target 缩略图。点击缩略图会在新的浏览器标签页中打开捕获图片。

小型设置按钮会打开自动捕获配置。当前类别包括 Hover、Zoom / Scroll、Click / Select、Change / Toggle 和 System。默认启用 Click / Select、Change / Toggle 和 System，默认关闭 Hover 和 Zoom / Scroll。捕获质量可以设置为 Thumbnail 或 Full。当前默认是 Full。

悬停动作会在记录前故意延迟，因此快速经过元素不会立刻产生记录。

### Annotations

Annotations 标签页列出通过相机按钮或 Option+S 快捷键创建的快照标注。每条标注会保存来源视图、时间戳、文字备注、快照支持选择时的选中项目，以及被捕获的草图图片。

标注卡片可以展开，以查看选中项目细节和完整草图图片。

### Action Tree

Action Tree 标签页把动作和标注显示为一棵可视化树。图例区分 System、Interact、Zoom/Scroll、Hover、Annotation 和 Other 节点。代币切换和快照更新会形成主要分支，之后的交互会挂在当前分支下。

相机形状的 **Create Finding** 按钮会开启标注节点多选模式。选择一个或多个标注节点，点击 Confirm，输入发现备注并保存。高层发现会重新加入标注记录，并且可以引用它所总结的标注。

点击标注节点会打开其细节。点击高层发现节点会打开发现文本及其引用的标注。

### LLM Analysis

LLM Analysis 标签页会显示 Codex 生成的 trace 分析 artifact。它会先向后端请求当前 analysis artifact manifest，然后从会话的 `artifacts` 文件夹加载 `reasoning-graph.json` 和所有可用的 `reasoning-graph-patch*.json` 文件。该标签页会在浏览器中验证 graph 和 patch，按确定顺序应用 patch，并派生出用于显示的 forest。生成的 forest JSON 或 Markdown 文件只作为可选导出，不再作为 UI 的数据源。未回答的 Analytic Question 会显示为非阻塞的 graph warning，因为用户 trace 可能尚未包含答案；重要且可回答的 warning 应由智能体继续调查，并通过 patch Finding 解决。该标签页渲染一个更紧凑的发现层级：顶层 Hypothesis 包含用户 Finding 和智能体生成的补丁 Finding，而内部的 Task、Analytic Question、Analytic Activity 和 Interaction 不会显示在卡片视图里。这些隐藏节点仍保留在源 graph 中用于追溯。回答隐藏 Analytic Question 的中层 Finding 仍会显示在 Finding 层级中；如果同一个 canonical Finding 因为隐藏节点投影而重复出现，界面会把它折叠为一个卡片，避免同一个答案在一个 Hypothesis 下重复显示。Finding 的来源会显示在节点标记中：用户 Finding 使用蓝色 `User Finding` 标记，智能体生成的补丁 Finding 使用粉色 `Agent Finding` 标记，来自补丁的 Hypothesis 会显示为粉色 `Derived Hypothesis`。关系标记会区分支持性证据、直接回答、细化结论和反驳关系。在后续每个 Codex 智能体回合开始时，该标签页会清除旧的 `New` 标记，记录当时可见的 Hypothesis 和 Finding，并给本回合中新出现的可见卡片添加小型 `New` 标记。如果初始 Full Analysis 开始时还没有任何卡片，系统会抑制这些标记，避免第一次生成 forest 时到处都是 `New`。Hypothesis 和 Finding 卡片还包含一个小型复选框，用于用户研究评价；勾选重复出现的 Finding 时，系统只保存一份 canonical evaluation，并让可见重复项保持同步。带有截图或渲染图 provenance 的卡片在展开时会显示小缩略图。点击卡片会打开细节，包括它与父节点的关系、可用的 evidence summary、patch rationale 和较大的证据图片。工具栏还提供 **Export JSON** 按钮，会先把当前分析包保存为会话 artifact，再使用稳定的 `.json` 文件名下载；该分析包包含已加载的 reasoning graph、按顺序应用的 patch 列表、augmented graph、当前复选框评价、`New` 标记 UI 状态，以及当前界面展示的 forest，便于后续离线分析和复查。Human Workspace 标记旁边的 `Analysis Import` 标签会在新页面打开导入界面；选择刚导出的 JSON 后，会按当前右侧 LLM Analysis 的方式恢复卡片层级和详情视图，便于单独查看与复盘。

`current-reasoning-graph.json` 是给智能体和调试使用的派生阅读辅助。LLM Analysis 标签页仍然以 `reasoning-graph.json` 加 patch 文件作为数据源。

该标签页会在打开时、点击 Refresh 时、Codex 宣布新的相关 artifact 时刷新；当标签页处于激活状态时，也会进行轻量级周期检查。在 Codex Chat 回合进行中，bridge 会大约每秒两次扫描会话 artifacts 并宣布新写入或更新的 artifact，所以有效的 `reasoning-graph.json` 可以在后续 patch 文件完成前先显示为卡片。后端不会启动长期文件监听器，而是在请求时扫描会话 artifacts 并返回最新识别到的文件。

## 快照标注工作流

三个主视图支持快照标注：Token Distribution、K-line 和 Behavior Details。可以使用视图标题栏中的相机按钮，也可以把鼠标放在支持的视图上并在 macOS 上按 Option+S。该快捷键在实现上是 Alt+S，因此实际键盘行为取决于操作系统和浏览器。

每个快照对话框都包含一个浮动工具栏。

- **Select / Lasso** 在快照类型支持选择时选择项目。
- **Pen** 绘制自由线条。
- **Box** 绘制矩形标注框。
- **Eraser** 删除附近的草图。
- 颜色色块可在红、蓝、绿、橙、黑之间切换。
- **Clear All** 删除当前快照中的所有草图标记。

Token 快照可以选择持有者节点并显示选中节点细节。Behavior 快照可以选择用户轨道或事件圆点，并显示选中项目细节。K-line 快照基于图像，主要支持草图绘制和文字备注。

输入文本并点击 Annotate 后，系统会保存标注，关闭快照对话框，并把中列下方的面板切换到 Annotations 标签页。文本可以为空，因此只包含草图的标注也可以被记录。

## 导出会话

标题栏中的 `Study Info` 按钮会打开实验元数据对话框，可填写 `Participant ID`、`Session Order` 和附加说明；condition 会根据当前工作区自动显示为 `baseline` 或 `full ManiScope`，dataset 会跟随当前 ACT / PNUT 选择。

标题栏中的 Export 按钮会打开 `Export Study Package` 对话框。对话框显示当前动作数量、标注数量和 chat turn 数量，并提供 **Include snapshot images (PNG)** 复选框。

- 启用该复选框时，导出的 zip 会尽可能保存完整实验材料，包括动作缩略图、标注草图、导出时的当前三大视图截图、聊天附图，以及可访问的聊天响应图片 artifact。JSON 中会保存类似 `images/action-0001-target-kline-chart-01.png` 的路径，而不是内联图片字符串。
- 对于 specialized 会话，导出的 zip 还会包含一份 `llmAnalysis` 快照：其中有原始 reasoning graph、patch graph、最后用于展示的 hypothesis / findings 层级，以及这些分析节点引用到的图片证据。
- zip 还会记录 `llmAnalysisTrace`：包括 user reasoning graph 首次返回 / 更新的时间，以及后续 findings patch 回来的时间；这些事件也会进入 `derivedTables.llmAnalysisTrace`，便于做 reasoning trace 分析。
- 禁用该复选框时，导出的 zip 仍然包含完整的结构化实验日志与元数据，但会移除嵌入图片内容。
- `session.json` 现在除了原始 `userActionSequence` 与 `annotationRecords` 外，还会包含 `studyInfo`、`analysisMilestones`、`chatbotLogs`、`llmAnalysisTrace`、导出时 `currentState`，以及便于后续统计分析的 `derivedTables.interactionTrace`、`derivedTables.userNotes`、`derivedTables.chatbotLogs`、`derivedTables.llmAnalysisTrace`。

点击 **Download ZIP** 会保存一个类似 `maniscope-session-ACT-YYYYMMDD-HHMMSS.zip` 的文件。压缩包内的 `session.json` 适合直接做用户实验后续分析，`images/` 目录则保存与之对应的证据图片。

标题栏中的 **Study Import** 会打开一个独立的新页面，用于导入 study-package zip 并只读恢复完整查看界面。这个页面不会覆盖你当前正在分析的 live session。导入后既可以查看恢复后的主工作区，也可以查看导出元数据、当前视图截图、analysis milestones、chat logs，以及 zip 中保存的 LLM Analysis 内容。

导入页中的 **Trace Timeline** 标签会把用户交互事件、LLM 请求到响应的时间窗口、assistant activity / reasoning 事件，以及 LLM Analysis 中 reasoning graph / findings patch 的返回时间并置到同一条时间轴上，方便观察 traces 的时序模式。如果归档里没有 activity 的原始时间戳，页面会在该轮请求-响应窗口内估算它们的位置，并明确标注为 estimated。

## Coin Selector

标题栏中的 ACT 和 PNUT 单选按钮用于切换当前数据集。切换代币会重置当前可视状态，清空选中用户和缓存结果，重新加载可用快照时间，选择最新可用时间，并为所选代币运行初始化流程。

代币切换会被记录为系统动作，也会在 Action Tree 中创建新分支。

## 检测规则参考

下面总结当前前端配置中的默认值。

### Entity Detection 默认值

| 规则族 | 默认状态 | 关键设置 |
|---|---:|---|
| Network Based | 关闭 | Direct Transfer 开启，Min Tx Count 开启且值为 3，Min Volume 关闭，Funding Relationship 开启 |
| Similarity Based | 开启 | Trading Action Sequence 关闭，Balance Sequence 开启且粒度为 1h、相似度为 0.6，Earning Sequence 关闭 |
| Manipulation Based | 关闭 | Max Manipulation Time Diff 为 2 |

### Link Configuration 默认值

| 规则族 | 默认状态 | 关键设置 |
|---|---:|---|
| Network Based | 关闭 | Direct Transfer 开启，Min Tx Count 开启且值为 1，Funding Relationship 关闭 |
| Similarity Based | 开启 | Trading Action Sequence 开启，Action Only，Min Seq Length 为 3，Max Time Diff 为 120 |
| Manipulation Based | 开启 | Max Manipulation Time Diff 为 120 |

### Manipulation Detection 默认值

| 参数 | Round Trip | Same Direction |
|---|---:|---:|
| Enabled | 是 | 是 |
| Max Time Diff | 120 | 10 |
| Max Position Diff | 100 | 不使用 |
| Max Earning | 1000 | 不使用 |
| Min Seq Length | 不使用 | 5 |
| Max Diff Direction | 不使用 | 0 |
| Entity Based | 是 | 是 |

## 推荐工作流

1. 在标题栏选择 ACT 或 PNUT。
2. 选择一个快照时间，并按需要调整持有者阈值。
3. 点击 Update Snapshot。这会刷新快照并重跑当前检测流程。
4. 扫视 Token Distribution 视图，关注密集的红色描边区域、橙色虚线实体边界和灰色链接。
5. 使用 K 线视图寻找 Round Trip 或 Same Direction 卡片密集的时间区间。
6. 点击可疑持有者节点或操纵卡片，以填充 Behavior Details。
7. 使用 Show Related Users、Sequential Time、Show Manipulation Boxes、缩放和 Sync Time，对比钱包行为与价格变化。
8. 当发现值得记录的证据时，从 Token Distribution、K-line 或 Behavior Details 视图打开快照。
9. 按需要添加标注文字、草图、选中节点或选中行为项目。
10. 使用 Action Tree 回顾调查路径，并把标注组合成高层发现。
11. 当动作轨迹和标注准备好共享时，导出会话 JSON。

## UI 上不容易看出的事项

Update Snapshot 不只是视觉刷新。它会获取快照数据，并使用当前设置重跑实体检测、链接检测和操纵检测。

当基于实体的操纵规则处于启用状态时，Entity Detection 下的 Run Detection 也可能更新操纵结果。这是因为实体变化会改变用于实体级操纵检测的合并交易序列。

中列下方的调查面板是分析状态的一部分。用户动作、标注和发现都是会话数据，也是 Export 工作流会序列化的内容。

Import 按钮在当前前端中可见但被禁用。代码中有解析和冲突处理辅助函数，但用户无法从可见 UI 触发它们。

Sequential Time 会改变 Behavior Details 横轴的含义。当你需要比较钱包之间的动作顺序时可以启用它。当你需要与 K 线时间严格对齐时，应关闭它。

Show Related Users 只会在单用户检查时出现。选择操纵卡片时，Behavior Details 会显示 Card Users。

仪表板目前仍然没有在主 UI 中展示钱包标签。如果某个头部持有者其实是交易所地址或合约地址，这会影响解释，但当前前端不会直接显示这些标签。

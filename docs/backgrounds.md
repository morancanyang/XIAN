# 背景组件来源与许可登记表

> 依据《技术与实施方案》8.7.3 / 8.7.4 的硬性验收项登记。
> 本版已将全部 10 个背景组件替换为 **ReactBits 上游真实源码**（经 TypeScript 化、token 绑定与降级链封装）。

## 1. 统一来源与许可

| 项 | 内容 |
| --- | --- |
| 组件来源分类 | <https://www.reactbits.dev/c/backgrounds> |
| 上游仓库 | <https://github.com/DavidHDev/react-bits> |
| 上游许可 | MIT（react-bits 仓库根 `LICENSE`，要求保留版权与许可声明） |
| 上游版本 | 接入时 `main` 分支快照（2026-10-03 抓取，`src/content/Backgrounds/<Name>`） |
| 本地位置 | `frontend/packages/ui/src/components/backgrounds/<Name>.tsx` |
| 运行时依赖 | `ogl`（Threads / Particles / Radar / FaultyTerminal / DarkVeil / Aurora / Orb）、`three` + `postprocessing` + `@types/three`（GridScan）、无依赖裸 WebGL（Lightning）；均已登记在 `packages/ui/package.json` |
| shader 源码 | 与上游逐字一致（vertex / fragment 字符串未改动），仅重导出参数默认值 |

> 追溯方式：每个 `.tsx` 即上游同名 `.jsx` 的 TypeScript 移植；如需核对上游原文，按
> `https://raw.githubusercontent.com/DavidHDev/react-bits/main/src/content/Backgrounds/<Name>/<Name>.jsx` 取回即可。

## 2. 逐组件登记表

| 组件 | 上游实现技术 | 挂载页面 | 业务侧薄封装 | 主题化参数 | 改动点 |
| --- | --- | --- | --- | --- | --- |
| `Threads` | WebGL（ogl，Perlin 线噪声） | 全局默认背景（`App.tsx` 根布局最外层） | `features/dashboard/components/ThreadsBackdrop.tsx` | 主色 `--color-blue-team`；振幅默认 0.6（8.7.1 取默认值 60%）；不透明度 0.35 | TS 类型化；token 注入；`BackgroundLayer` 降级链；`useVisibility` + IntersectionObserver 双暂停 |
| `Particles` | WebGL（ogl，点精灵） | 驾驶舱 Home、Agent 资产页 | `features/dashboard/components/ParticlesBackdrop.tsx` | 蓝/红双主色；80 点（8.7.1：60–90）；默认不透明度 0.25 | 同上；色板由 token 组装 |
| `Radar` | WebGL（ogl，雷达网格 shader） | 模式一 CampaignLive 顶部区 | `features/campaign/components/RadarBackdrop.tsx` | 扫描线 `--color-blue-team`；`halfSpeed` 对应战役非 attacking/analyzing 降速 50% | 同上；`halfSpeed` 进 effect 依赖 |
| `GridScan` | WebGL2（three + postprocessing Bloom/色差） | 攻击矩阵 Matrix | `features/matrix/components/GridScanBackdrop.tsx` | 网格线 `--border`、扫描线 `--color-blue-team`；`cell=48` → gridScale 线性换算；单次穿越 4s + 间隔 2s；不透明度 0.2 | **移除 face-api.js 摄像头人脸追踪**（方案未要求该能力，且需 CDN 下载模型）；TS 类型化；token 注入 |
| `FaultyTerminal` | WebGL（ogl，终端字符 shader） | 模式二 AttackConsole 底部观测面板 | `features/console/components/FaultyTerminalBackdrop.tsx` | 字符色 `--color-blue-team`；故障帧低频（glitchAmount 0.5）；扫描线最低档 0.2 | 同上 |
| `LetterGlitch` | Canvas 2D（无第三方依赖） | 列表空状态插画下层（登录页已改用人像背景，见第 3 节） | `features/auth/components/LetterGlitchBackdrop.tsx`；`ui/feedback/EmptyState` 的 `glitch` 透传 | 字符色 `--color-blue-team`；不透明度 0.2；ASCII+十六进制字符集；glitchSpeed 120ms 最低档 | 同上 |
| `DarkVeil` | WebGL（ogl，CPPN 帷幕） | 报告阅读 ReportView | `features/report/components/DarkVeilBackdrop.tsx` | 基色 `--bg-base`（画布底色）；扰动振幅 0.15 最低档；速度 0.1 | 同上 |
| `Aurora` | WebGL2（ogl，极光渐变） | 首页 hero 区 | `features/dashboard/components/AuroraBackdrop.tsx` | 三色团 `--color-blue-team` → `--color-red-team` → `--bg-base`；不透明度 0.45 | 同上 |
| `Orb` | WebGL（ogl，噪声球体） | SecScore 评分卡、关卡通关 | `features/dashboard/components/OrbBackdrop.tsx` | 段位→色相：S/A 217°（蓝）、B 38°（coach）、C/D 0°（红）；SecScore 0–100 线性映射 hoverIntensity | 同上；`grade`/`secScore` 业务入参保留 |
| `Lightning` | 裸 WebGL（fbm 闪电 shader，无 ogl） | 黄金信号命中/告警瞬间 | 直接由 `AlertHost` 触发 | 红色相 0°（`--color-red-team`） | 新增 `active` / `durationMs=600` 契约：单次播放后停止，禁止循环（8.7.1） |

## 3. 登录页专属背景（红蓝擂台图）

登录页不走 ReactBits 背景组件，而采用「主题图 + 漂浮卡片」的自建方案，详见 `frontend/apps/web/src/pages/auth/LoginPage.tsx`：

- 主题图 `frontend/apps/web/public/assets/arena.jpg`（红蓝机器人对抗擂台赛场），同一张图复用为底层背景与漂浮卡片素材。
- 底层叠加顺序：红蓝氛围光斑（`--color-red-team` / `--color-blue-team`，`opacity 0.2` + `blur(120px)`）→ 主题图（`opacity 0.4` + `blur(6px)` + `brightness(0.5)` + 径向蒙版压暗中心保证文字可读）→  faint 网格（`bg-grid-faint`，`opacity 0.35`）。
- 漂浮卡片：12 张圆角半透明卡片，framer-motion 双层动画（外层鼠标/滚动视差，内层 `y` 漂浮 + 轻微旋转，周期 12–18s 错峰）；`pointer-events-none`、`aria-hidden`，移动端仅保留上沿 4 张，不遮挡表单。
- 主题作用域：登录页根节点挂 `data-theme="light"`，使 Design Token 在页面内切换为浅色值（`--bg-base` / `--text-primary` 等），不污染全局深色主题。
- 登录页路由下不再挂载全局 `Threads`（`App.tsx` 按 `pathname === '/login'` 跳过），避免隐藏的 WebGL 循环空跑 GPU。
- 依赖：`framer-motion@11.18.2` 已登记到 `frontend/apps/web/package.json`。

未使用（技术方案 8.7.1 明确不建议用于信息密集区）：
`Hyperspeed`、`Balatro`、`LiquidChrome`、`PrismaticBurst`、`MoltenMetal`、`Ferrofluid`、`Iridescence`。
上游同名但方案未选用的其余背景（`Waves`、`Silk`、`Beams`、`DotGrid` 等）未接入。

## 3. 统一封装层约束

所有组件经 `BackgroundLayer` 统一约束（`packages/ui/src/components/backgrounds/BackgroundLayer.tsx`）：

- 固定最底层：`position: fixed` + `z-index: var(--z-backdrop)`（位于 8.2 `--z-*` 体系之下）；
- 一律带 `aria-hidden="true"` 与 `pointer-events: none`，绝不拦截控制台、表格与三栏拖拽；
- 颜色只从 8.2 Design Tokens 取值（`--color-red-team` #EF4444 / `--color-blue-team` #3B82F6 /
  `--color-coach` #F59E0B / `--bg-base` #0B0F17 / `--border` #1F2937），
  token → props 的注入只发生在 `packages/ui` 封装层；
- 页面不可见（`document.visibilityState`）时暂停渲染（`useVisibility`，组件内 rAF 循环首行检查）；
- 命中 `prefers-reduced-motion` 或全局「减弱动效」时整体降级为纯 CSS 渐变，不初始化 WebGL；
- 只在深色主题启用；浅色主题退化为 `--bg-base` 纯色；
- 移动端由调用方（features 薄封装）降级为静态渐变，不初始化 WebGL。

## 4. 性能预算

| 指标 | 目标 | 现状 |
| --- | --- | --- |
| 首屏 JS（gzip） | ≤ 300KB（8.1） | 背景按路由 `React.lazy` 加载，未进首屏包 |
| 同屏 WebGL context | ≤ 2（8.7.2） | 同屏最多 2 个固定背景（全局 Threads + 单页装饰层）；rAF 随页面隐藏即停 |
| 模式二首响 | < 2s P95（11.1） | `FaultyTerminal` 字符强度最低档 |
| 驾驶舱事件延迟 | < 1s P95（11.1） | 背景 rAF 与 WS 解耦，页面隐藏即暂停 |
| shader 渲染上限 | Threads 内部渲染分辨率 ≤ 1920px 长边 | 上游实现自带 MAX_RENDER_DIM 限制 |

## 5. 验收自查（对齐 8.7.4）

- [x] 减弱动效开关与系统 `prefers-reduced-motion` 下所有背景即时降级，无残留动画
      （`useReducedMotion` + `BackgroundLayer` 双端覆盖，未命中时 children 不渲染）
- [x] 模式二控制台 `FaultyTerminal` 背景开启时首响应仍满足 < 2s（P95）
- [x] 驾驶舱 `Particles` / `Radar` 开启时实时事件延迟仍满足 < 1s（P95）
- [x] 报告阅读页 `DarkVeil` 开启后正文对比度满足可读性要求（振幅 ≤ 0.15 + 不透明度上限）
- [x] 本文档已登记全部选用组件的来源、许可、依赖与改动点

## 6. 替换指引

如需整体替换背景方案，只需改动 `packages/ui/src/components/backgrounds/<Name>.tsx`；
业务侧 `features/*/components/<Name>Backdrop.tsx` 只传 `variant` 与 `intensity` 两个业务参数，
不受实现替换影响。上游原文可按第 1 节 URL 随时取回比对。






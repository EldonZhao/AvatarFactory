# Avatar养成记

基于 Astro 5 + React 19 的静态阅读型子网站，用于展示 AvatarFactory 系统中的 Avatar 养成全过程。

## 快速开始

```bash
cd web
npm install
npm run dev      # 开发模式 http://localhost:4321
npm run build    # 构建生产版本
npm run preview  # 预览生产版本
```

## 功能特性

- **仪表板** - Avatar 概览、统计数据、最新动态
- **Avatar 列表** - 卡片网格展示所有人设
- **Avatar 详情** - 人设信息、内容支柱、版本历史
- **内容展示** - 草稿/发布内容、Markdown 渲染、审核报告
- **时间线** - 操作历史记录
- **调度任务** - 周期任务列表与状态
- **统计分析** - 可视化图表

## 技术栈

- **框架**: Astro 5 + React 19
- **样式**: Tailwind CSS 4
- **动画**: Framer Motion
- **图表**: Recharts
- **数据源**: 读取 `../knowledges/` 目录的 YAML/JSON 数据

## 目录结构

```
web/
├── src/
│   ├── layouts/          # Astro 布局
│   ├── pages/            # 页面路由
│   ├── components/       # React 组件
│   │   ├── ui/           # 基础 UI 组件
│   │   ├── layout/       # 布局组件
│   │   ├── dashboard/    # 仪表板组件
│   │   ├── avatar/       # Avatar 相关
│   │   ├── content/      # 内容相关
│   │   ├── timeline/     # 时间线
│   │   ├── scheduler/    # 调度任务
│   │   └── stats/        # 统计图表
│   ├── lib/
│   │   ├── data/         # 数据读取层
│   │   ├── types/        # TypeScript 类型
│   │   └── utils/        # 工具函数
│   └── styles/           # 全局样式
└── public/               # 静态资源
```

## 主题

支持亮色/暗色主题切换，点击右上角的主题按钮即可切换。

## 数据源

网站在构建时读取 `../knowledges/` 目录中的数据：

- `personas/{id}/config.yaml` - 人设配置
- `personas/{id}/content/drafts/` - 草稿内容
- `personas/{id}/content/published/` - 已发布内容
- `personas/{id}/reviews/` - 审核报告
- `personas/{id}/history.json` - 版本历史
- `scheduler/tasks.json` - 调度任务

可通过环境变量 `KNOWLEDGE_BASE_PATH` 自定义数据目录路径。

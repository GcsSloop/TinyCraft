# Nano Banana Pro 网页编辑器

本项目目标是实现一个基于 nano banana pro 的网页编辑器：浏览器直接读取本地文件，用户选择文件区域并输入替换内容，显示修改进度，完成后给出预览链接。除 API 服务外，文件不上传到任何托管服务器。

## 技术栈

- 前端：Vue + Element
- 后端：Python

## 如何使用 skill

本项目的 skill 位于 `skills/tiny-craft/SKILL.md`，用于规范后续开发流程与约束。

使用方式：

1. 在与 Codex 交互时，明确提到该 skill 名称（`tiny-craft`）。
2. Codex 会根据 skill 的指引拆分前后端工作并遵守本地优先与隐私约束。
3. 若有新的 API 规范或编辑器方案，先补充到 skill 的 `references/` 下，再继续开发。

## 后端运行

1. 安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. 启动服务：

```bash
sh backend/run.sh
```

## 前端启动与调试

1. 安装依赖：

```bash
cd frontend
npm install
```

2. 启动开发服务：

```bash
npm run dev
```

3. 访问调试：

打开 `http://127.0.0.1:5173`，前端会通过 Vite 代理访问后端 `http://127.0.0.1:8000`。

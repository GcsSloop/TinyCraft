---
name: tiny-craft
description: Build a web editor based on nano banana pro with a Python backend and Vue + Element frontend, emphasizing local file selection, in-browser editing/preview, and no file uploads except to the API server.
---

# Nano Banana Pro 网页编辑器 Skill

用于实现一个浏览器内编辑器：直接读取本地文件，选取文件区域并输入替换内容，展示修改进度并在完成后提供预览链接，同时保证文件不上传到任何托管服务器，除 API 服务端外不外传。

## 范围与约束

- **本地优先**：浏览器读取本地文件，优先使用 File System Access API，兼容 `<input type="file">`。每次更新将完整文件发送给 API，并附带选区与描述内容。
- **禁止第三方托管**：不上传至外部存储/CDN，唯一远程端点是 API 服务。
- **进度与预览**：修改任务应有进度提示，完成后提供预览链接（如 Blob URL 或本地下载）。

## 前端（Vue + Element）指引

- **文件选择**：优先使用 File System Access API，回退到文件输入控件。
- **编辑与选区**：展示文件内容，允许用户选区（起止或范围），并填写替换内容。
- **任务提交**：提交修改任务给后端；进度采用 SSE 或轮询。
- **预览与下载**：使用浏览器端 Blob URL 进行预览，必要时提供下载。

## 后端（Python）指引

- **接口输入**：接收完整文件内容 + 选区范围 + 替换内容/描述信息。
- **调用处理**：把完整文件传给 nano banana pro（本地库或外部 API），返回进度更新。
- **结果返回**：返回修改后的完整文件或完整内容片段，供前端更新预览与下载。
- **框架约束**：后端使用 FastAPI，接口规范通过 FastAPI 自动生成 Swagger 文档（OpenAPI）。

## Nano Banana（Gemini Image）接入要点

- **模型选择**：Nano Banana = `gemini-2.5-flash-image`；Nano Banana Pro = `gemini-3-pro-image-preview`。
- **输入形态**：支持文本、图片或两者组合；编辑场景建议传入原图 + 文本描述。
- **多图限制**：Pro 预览版最多 14 张参考图（其中最多 5 张高保真人物/对象图）。
- **输出形态**：默认返回文本 + 图片，可配置仅图片；生成图片均包含 SynthID 水印。
- **可选配置**：`aspect_ratio`（如 `16:9`），`image_size`（`1K`/`2K`/`4K`，需大写 K），`response_modalities`。
- **多轮对话**：如使用对话/多轮生成，需保留并回传 `thought_signature`（若 SDK 自动处理可忽略）。
- **接地搜索**：可选开启 Google Search 工具，用于基于实时信息生成图片。

## 实施流程

1. **确认 nano banana pro 接入方式**
   - 本地库或外部 API。
   - 输入输出形式（全量文件）。
2. **定义任务协议**
   - 请求：完整文件、选区范围、替换内容/描述信息。
   - 响应：任务 id、进度事件、完成时的修改后文件。
3. **前端流程**
   - 选择文件并展示内容 -> 选区 -> 输入替换内容 -> 提交任务 -> 展示进度 -> 预览与下载。
4. **后端流程**
   - 校验范围 -> 调用 nano banana pro（附带完整文件） -> 输出进度 -> 返回修改后的文件。
5. **隐私与安全**
   - 服务器端不落地保存原始文件。
   - 仅保存完成任务所需的短暂数据。

## 配置文件规范

- **存放位置**：
  - 非敏感配置：`backend/config/app.yaml`
  - 敏感配置：`backend/.env`（不提交到仓库）
- **建议存储信息**：
  - `NANO_BANANA_API_KEY`：Gemini API Key（敏感）
  - `NANO_BANANA_MODEL`：默认模型（如 `gemini-3-pro-image-preview`）
  - `NANO_BANANA_BASE_URL`：API 基地址（如需自定义）
  - `NANO_BANANA_TIMEOUT`：请求超时（秒）
  - `NANO_BANANA_MAX_IMAGES`：单次最大图片数量
  - `NANO_BANANA_ASPECT_RATIO`：默认宽高比
  - `NANO_BANANA_IMAGE_SIZE`：默认分辨率（`1K`/`2K`/`4K`）
  - `NANO_BANANA_RESPONSE_MODALITIES`：默认输出类型（`TEXT,IMAGE` 或 `IMAGE`）
  - `NANO_BANANA_ENABLE_SEARCH`：是否启用 Google Search 接地

## 参考文件添加时机

- 如有 nano banana pro API 规范，添加 `references/nano-banana-pro-api.md` 并在此链接。
- 如需特定编辑器或 diff/patch 方案，添加 `references/editor.md`。

# M3U8 Downloader Docker Image

## 概述
该项目是一个使用 Python 编写的 M3U8 视频下载器，能够从 M3U8 URL 下载视频片段并将它们合并成一个完整的视频文件。此项目利用 Docker 容器化技术，方便在不同平台上部署和运行。

## 如何使用

### 前提条件
- 你需要一个 Docker Hub 账户。
- 你需要将你的 Docker Hub 用户名和密码存储在 GitHub 仓库的 Secrets 中。

### 配置 GitHub Action
1. **添加 Docker Hub 凭据到 GitHub Secrets**：
    - 在你的 GitHub 仓库中，导航至 `Settings` -> `Secrets`。
    - 创建两个新的 Secrets：
        - `DOCKERHUB_USERNAME`：存储你的 Docker Hub 用户名。
        - `DOCKERHUB_TOKEN`：存储你的 Docker Hub 密码或访问令牌。

2. **使用 GitHub Action 自动构建和推送 Docker 镜像**：
    - 当你将代码推送到 `main` 分支或向 `main` 分支发起拉取请求时，GitHub Action 会自动触发。
    - 该工作流将使用 `docker/setup-buildx-action` 构建多平台 Docker 镜像，并将其推送到 Docker Hub。

### 本地运行 Docker 容器
要在本地运行 Docker 容器，请使用以下命令，并设置 `M3U8_URL` 和 `OUTPUT_DIR` 环境变量：
```bash
docker run -e M3U8_URL="your_m3u8_url" -e OUTPUT_DIR="your_output_dir" your_dockerhub_username/m3u8-downloader:latest
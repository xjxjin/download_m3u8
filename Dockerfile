# 使用 Python 精简版作为基础镜像
FROM python:3.10-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖，包括 ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装 Python 依赖
RUN pip install requests,logging

# 运行 Python 脚本
CMD ["python", "download_m3u8.py"]
# 使用 Python 精简版作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 设置 Chrome 无头模式需要的环境变量
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir \
    flask \
    requests \
    selenium \
    webdriver-manager

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 暴露端口
EXPOSE 5000

# 设置启动命令
CMD ["python", "app.py"]
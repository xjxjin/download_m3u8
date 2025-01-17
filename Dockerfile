# 使用 Python 精简版作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg2 \
    unzip \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 尝试安装 Google Chrome，如果失败则安装 Chromium
RUN set -ex; \
    if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1"."$2"."$3}') && \
        DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
            jq -r --arg ver "$CHROME_VERSION" '.versions[] | select(.version==$ver) | .downloads.chromedriver[] | select(.platform=="linux64") | .url') && \
        if [ -n "$DRIVER_URL" ]; then \
            wget -q "$DRIVER_URL" -O /tmp/chromedriver.zip && \
            unzip /tmp/chromedriver.zip -d /tmp/ && \
            mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
            chmod +x /usr/local/bin/chromedriver && \
            rm -rf /tmp/chromedriver* && \
            echo "Chrome and ChromeDriver installed successfully"; \
        else \
            echo "ChromeDriver not found for version $CHROME_VERSION, installing Chromium instead" && \
            apt-get install -y chromium chromium-driver; \
        fi \
    else \
        echo "Architecture is not amd64, installing Chromium instead" && \
        apt-get update && \
        apt-get install -y chromium chromium-driver; \
    fi && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get purge -y wget unzip curl jq && \
    apt-get autoremove -y

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 设置浏览器环境变量
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV CHROMIUM_BIN=/usr/bin/chromium
ENV CHROMIUM_DRIVER_PATH=/usr/bin/chromedriver

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装 Python 依赖
#RUN pip install --no-cache-dir -r requirements.txt
# 安装 Python 依赖
RUN pip install --no-cache-dir \
    flask \
    requests \
    selenium \
    webdriver-manager


# 创建必要的目录
RUN mkdir -p /app/downloaded_m3u8 && \
    chmod 777 /app/downloaded_m3u8

# 暴露端口
EXPOSE 5020

# 设置启动命令
CMD ["python", "app.py"]
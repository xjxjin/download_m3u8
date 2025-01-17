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
    && rm -rf /var/lib/apt/lists/*

# 尝试安装 Google Chrome，如果失败则安装 Chromium
RUN set -ex; \
    if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1}') && \
        wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION.0.6261.94/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /tmp/ && \
        mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
        chmod +x /usr/local/bin/chromedriver && \
        rm -rf /tmp/chromedriver* && \
        echo "Chrome and ChromeDriver installed successfully"; \
    else \
        echo "Architecture is not amd64, installing Chromium instead" && \
        apt-get update && \
        apt-get install -y chromium chromium-driver; \
    fi && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get purge -y wget unzip && \
    apt-get autoremove -y

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 根据安装的浏览器设置环境变量
RUN if [ -f "/usr/bin/google-chrome" ]; then \
        echo "export CHROME_BIN=/usr/bin/google-chrome" >> /etc/environment && \
        echo "export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver" >> /etc/environment; \
    else \
        echo "export CHROME_BIN=/usr/bin/chromium" >> /etc/environment && \
        echo "export CHROMEDRIVER_PATH=/usr/bin/chromedriver" >> /etc/environment; \
    fi

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir \
    flask \
    requests \
    selenium \
    webdriver-manager

# 暴露端口
EXPOSE 5020

# 设置启动命令
CMD ["python", "app.py"]
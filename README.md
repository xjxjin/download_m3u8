# M3U8 下载器

## 项目简介
这是一个基于 Python + Flask 的 Web 应用程序，用于下载和管理 M3U8 视频。主要功能包括：
- 自动提取网页中的 M3U8 链接
- 自动获取视频标题
- 下载并合并视频片段
- 文件管理（重命名、删除、下载等）

## 快速开始

### 使用 Docker Compose 运行
1. 克隆项目：
```bash
git clone https://github.com/xjxjin/download_m3u8.git
cd downloader_m3u8
```

2. 创建下载目录：
```bash
mkdir -p downloads
```

3. 启动服务：
```bash
docker-compose up -d
```

4. 访问应用：
打开浏览器访问 `http://localhost:5020`

### 目录结构
```
downloads/           # 下载的视频文件存储目录
├── videos/         # 视频文件
└── logs/          # 日志文件
```

## 使用说明

1. **获取 M3U8 链接**：
   - 在网页 URL 输入框中输入视频页面地址
   - 点击"获取 M3U8 URL"按钮
   - 系统会自动提取 M3U8 链接和视频标题

2. **下载视频**：
   - 确认 M3U8 链接和视频标题无误
   - 点击"立即执行"按钮开始下载
   - 等待下载完成

3. **文件管理**：
   - 点击"查看文件"可以浏览所有下载的视频
   - 支持文件重命名、删除和下载操作
   - 可以浏览不同目录层级

## 环境变量配置

可以通过修改 `docker-compose.yml` 文件来配置以下环境变量：
- `OUTPUT_DIR`: 视频输出目录（默认：/app/downloads）
- `PYTHONUNBUFFERED`: Python 输出缓冲设置
- `DISPLAY`: X11 显示设置

## 注意事项
- 确保有足够的磁盘空间用于存储下载的视频
- 下载大文件时可能需要等待较长时间
- 建议使用现代浏览器访问 Web 界面

## 贡献指南
欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证
MIT License
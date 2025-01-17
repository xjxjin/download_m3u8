import subprocess
import os
import sys
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler

# 设置默认输出目录
output_dir = os.getenv("OUTPUT_DIR", "downloaded_m3u8")
# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)


def setup_logger():
    """配置日志记录器"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 创建日志目录
    log_dir = os.path.join(current_dir, f'{output_dir}/log')
    os.makedirs(log_dir, exist_ok=True)

    # 设置日志文件路径
    log_file = os.path.join(log_dir, 'output.log')

    # 创建 TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )

    # 创建控制台处理器
    console_handler = logging.StreamHandler()

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# 初始化日志记录器
logger = setup_logger()


def execute_ffmpeg(input_url, output_file):
    # 构建 ffmpeg 命令
    command = [
        'ffmpeg',
        '-i', input_url,
        '-c', 'copy',
        output_file
    ]
    try:
        # 执行 ffmpeg 命令
        logger.info(f"执行的命令: {command}")
        subprocess.run(command, check=True)
        logger.info(f"成功将 {input_url} 转换为 {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 ffmpeg 命令时出错: {e}")
    except Exception as e:
        logger.error(f"发生了意外错误: {e}")


if __name__ == "__main__":
    # 从环境变量获取 m3u8_url 和 video_title
    m3u8_url = os.getenv("M3U8_URL")
    video_title = os.getenv("VIDEO_TITLE", "")
    
    if not m3u8_url:
        logger.error("请设置环境变量 M3U8_URL")
        sys.exit(1)
    
    # 生成输出文件名
    nowtime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # 确保输出目录存在
    os.makedirs(f"{output_dir}/videos", exist_ok=True)
    if video_title:
        output_file = f"{output_dir}/videos/{video_title}_{nowtime}.mp4"
    else:
        output_file = f"{output_dir}/videos/merged_video_{nowtime}.mp4"
    
    logger.info(f"output_dir: {output_dir}")
    logger.info(f"output_file: {output_file}")
    execute_ffmpeg(m3u8_url, output_file)

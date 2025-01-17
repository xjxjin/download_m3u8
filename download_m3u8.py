import os
import sys
import subprocess
import datetime
import logging
import requests
import re
from logging.handlers import TimedRotatingFileHandler

# 设置默认输出目录
output_dir = os.getenv("OUTPUT_DIR", "downloaded_m3u8")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/videos", exist_ok=True)

def setup_logger():
    """配置日志记录器"""
    logger = logging.getLogger('m3u8_downloader')
    logger.setLevel(logging.INFO)
    
    # 创建日志目录
    log_dir = os.path.join(output_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 文件处理器
    log_file = os.path.join(log_dir, 'downloader.log')
    file_handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

def get_total_segments(m3u8_url):
    """获取m3u8文件中的总片段数"""
    try:
        response = requests.get(m3u8_url)
        response.raise_for_status()
        content = response.text
        # 计算.ts文件的数量
        ts_count = len(re.findall(r'\.ts', content))
        return ts_count
    except Exception as e:
        logger.error(f"获取片段数失败: {str(e)}")
        return 0

def execute_ffmpeg(m3u8_url, output_file):
    """使用ffmpeg下载并合并视频片段"""
    try:
        # 获取总片段数
        total_segments = get_total_segments(m3u8_url)
        if total_segments > 0:
            logger.info(f"预计总片段数: {total_segments}")
        
        # 准备ffmpeg命令
        command = [
            'ffmpeg',
            '-i', m3u8_url,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            output_file
        ]
        
        # 使用subprocess.Popen来实时获取输出
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 初始化计数器
        frame_count = 0
        processed_lines = set()  # 用于存储已处理的行，避免重复计数
        
        # 实时读取输出
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                # 检查是否包含frame且该行未被处理过
                if 'frame=' in line and line not in processed_lines:
                    frame_count += 1
                    processed_lines.add(line)
                    
                    # 如果知道总片段数，计算进度百分比
                    if total_segments > 0:
                        progress = min(100, (frame_count / total_segments) * 100)
                        logger.info(f"下载进度: {progress:.2f}% ({frame_count}/{total_segments})")
                    else:
                        logger.info(f"已下载片段: {frame_count}")
        
        # 等待进程完成
        process.wait()
        
        if process.returncode == 0:
            logger.info(f"下载完成: {output_file}")
            logger.info(f"总共处理片段: {frame_count}")
            return True
        else:
            logger.error("下载失败")
            return False
            
    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        return False

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

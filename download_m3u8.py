import os
import sys
import subprocess
import datetime
import logging
import requests
import re
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import urljoin
import json

# 设置默认输出目录
output_dir = os.getenv("OUTPUT_DIR", "downloaded_m3u8")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/videos", exist_ok=True)

# 添加进度文件路径
progress_file = os.path.join(output_dir, 'download_progress.json')

def setup_logger():
    """配置日志记录器"""
    logger = logging.getLogger('m3u8_downloader')
    
    # 如果logger已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger
        
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


def get_m3u8_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"获取M3U8文件失败: {e}")
        return None


def parse_m3u8(content, base_url):
    lines = content.splitlines()
    segments = []
    for line in lines:
        if line.startswith('#EXT-X-STREAM-INF'):
            next_line = next((l for l in lines if l), None)
            if next_line:
                new_url = urljoin(base_url, next_line)
                new_content = get_m3u8_content(new_url)
                if new_content:
                    segments.extend(parse_m3u8(new_content, new_url))
        elif not line.startswith('#'):
            segment_url = urljoin(base_url, line)
            segments.append(segment_url)
    return segments


def get_total_segments(m3u8_url):
    """获取m3u8文件中的总片段数，包括处理嵌套的m3u8文件"""
    try:
        segments = []
        m3u8_content = get_m3u8_content(m3u8_url)
        if m3u8_content:
            segments = parse_m3u8(m3u8_content, m3u8_url)
            # download_segments(segments, segment_path)
            # merge_segments(output_dir, segment_path, output_file)
        return len(segments)

    except Exception as e:
        logger.error(f"获取片段数失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


def update_progress(progress, current_segments=None, total_segments=None, status='downloading', error=None):
    """更新下载进度"""
    try:
        progress_data = {
            'progress': progress,
            'current_segments': current_segments,
            'total_segments': total_segments,
            'status': status,
            'error': error
        }
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
    except Exception as e:
        logger.error(f"更新进度失败: {str(e)}")


def execute_ffmpeg(m3u8_url, output_file):
    """使用ffmpeg下载并合并视频片段"""
    try:
        # 获取总片段数
        total_segments = get_total_segments(m3u8_url)
        if total_segments > 0:
            logger.info(f"预计总片段数: {total_segments}")
            update_progress(0, 0, total_segments)

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
        processed_lines = set()

        # 实时读取输出
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if line:
                logger.info(line)
                if 'hls @' in line and line not in processed_lines:
                    frame_count += 1
                    processed_lines.add(line)
                    logger.info(f"总片数：{total_segments}  已完成数：{frame_count}")

                    # 更新进度
                    if total_segments > 0:
                        progress = min(100, (frame_count / total_segments) * 100)
                        update_progress(
                            progress=progress,
                            current_segments=frame_count,
                            total_segments=total_segments
                        )
                        logger.info(f"下载进度: {progress:.2f}% ({frame_count}/{total_segments})")
                    else:
                        logger.info(f"已下载片段: {frame_count}")

        # 等待进程完成
        process.wait()

        if process.returncode == 0:
            logger.info(f"下载完成: {output_file}")
            logger.info(f"总共处理片段: {frame_count}")
            update_progress(100, frame_count, total_segments, status='completed')
            return True
        else:
            logger.error("下载失败")
            update_progress(0, frame_count, total_segments, status='failed', error="FFmpeg 执行失败")
            return False

    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        update_progress(0, 0, total_segments, status='failed', error=str(e))
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

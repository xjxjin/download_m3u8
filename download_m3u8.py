import requests
import subprocess
import os
from urllib.parse import urljoin
import sys
import datetime
import time
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logger():
    """配置日志记录器"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 创建日志目录
    log_dir = os.path.join(current_dir, 'data/log')
    os.makedirs(log_dir, exist_ok=True)

    # 设置日志文件路径
    log_file = os.path.join(log_dir, 'alist_sync.log')

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


def get_m3u8_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"获取M3U8文件失败: {e}")
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


def download_segments123(segments, segment_path):
    if not os.path.exists(segment_path):
        os.makedirs(segment_path)
    for i, segment_url in enumerate(segments):
        segment_file = os.path.join(segment_path, f"segment_{i}.ts")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
            }
            with open(segment_file, 'wb') as f:
                response = requests.get(segment_url, stream=True, headers=headers)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"下载片段 {i + 1} 完成: {segment_url}")
        except requests.RequestException as e:
            logger.error(f"下载片段 {i + 1} 失败: {e}")
            # print(f"下载片段 {i + 1} 失败: {e}")

def download_segments234(segments, segment_path):
    if not os.path.exists(segment_path):
        os.makedirs(segment_path)
    for i, segment_url in enumerate(segments):
        segment_file = os.path.join(segment_path, f"segment_{i}.ts")
        try:
            headers = {
                'User - Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
            }
            response = requests.get(segment_url, stream = True, headers = headers)
            response.raise_for_status()
            total_size = int(response.headers.get('Content - Length', 0))
            downloaded_size = 0
            with open(segment_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size = 8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
            if total_size!= 0 and downloaded_size!= total_size:
                logger.error(f"下载片段 {i + 1} 不完整: {segment_url}，预期大小: {total_size}，实际下载大小: {downloaded_size}")
            else:
                logger.info(f"下载片段 {i + 1} 完成: {segment_url}")
        except requests.RequestException as e:
            logger.error(f"下载片段 {i + 1} 失败: {e}")


def download_segments(segments, segment_path):
    if not os.path.exists(segment_path):
        os.makedirs(segment_path)
    for i, segment_url in enumerate(segments):
        segment_file = os.path.join(segment_path, f"segment_{i}.ts")
        try:
            headers = {
                'User - Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
            }
            response = requests.get(segment_url, stream = True, headers = headers)
            response.raise_for_status()
            total_size = int(response.headers.get('Content - Length', 0))
            downloaded_size = 0
            with open(segment_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size = 8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
            if total_size!= 0 and downloaded_size!= total_size:
                logger.error(f"下载片段 {i + 1} 不完整: {segment_url}，预期大小: {total_size}，实际下载大小: {downloaded_size}")
            else:
                logger.info(f"下载片段 {i + 1} 完成: {segment_url}")
        except requests.RequestException as e:
            logger.error(f"下载片段 {i + 1} 失败: {e}")




def merge_segments123(output_dir, segment_path, output_file):
    segment_files = [os.path.join(segment_path, f) for f in sorted(os.listdir(segment_path)) if
                     f.endswith('.ts')]
    segment_list = f'{segment_path}/segment_list.txt'
    with open(segment_list, 'w') as f:
        for segment_file in segment_files:
            f.write(f"file '{segment_file}'\n")
    try:
        logging.info(f"尝试合并文件，输入文件列表: {segment_files}")
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', segment_list,
                        '-c', 'copy', f"{output_dir}/{output_file}"], check=True)
        logger.info(f"合并完成，输出文件: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"合并失败: {e}")
        if e.stderr:
            logger.error(f"ffmpeg 命令输出: {e.stderr.decode()}")
        else:
            logger.error("ffmpeg 没有标准错误输出")
    # finally:
    # if os.path.exists(segment_list):
    #     os.remove(segment_list)
    # if os.path.exists(segment_path):
    #     os.remove(segment_path)


def merge_segments(output_dir, segment_path, output_file):
    segment_files = [os.path.join(segment_path, f) for f in sorted(os.listdir(segment_path)) if
                     f.endswith('.ts')]
    segment_list = os.path.join(segment_path, "segment_list.txt")
    with open(segment_list, 'w') as f:
        for segment_file in segment_files:
            f.write(f"file '{segment_file}'\n")
    try:
        logging.info(f"尝试合并文件，输入文件列表: {segment_files}")
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', segment_list,
                        '-c', 'copy', os.path.join(output_dir, output_file)], check = True)
        logger.info(f"合并完成，输出文件: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"合并失败: {e}")
        if e.stderr:
            logger.error(f"ffmpeg 命令输出: {e.stderr.decode()}")
        else:
            logger.error("ffmpeg 没有标准错误输出")


if __name__ == "__main__":
    # 从环境变量获取 m3u8_url 和 output_dir
    m3u8_url = os.getenv("M3U8_URL")
    output_dir = os.getenv("OUTPUT_DIR", "downloaded_segments")
    # output_file = "merged_video.mp4"
    nowtime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    output_file = f"merged_video_{nowtime}.mp4"
    if not m3u8_url:
        print("请设置环境变量 M3U8_URL")
        sys.exit(1)
    segment_path = f"{output_dir}/tmp"
    logger.info(f"output_dir: {output_dir}")
    logger.info(f"segment_path: {segment_path}")
    logger.info(f"output_file: {output_file}")

    m3u8_content = get_m3u8_content(m3u8_url)
    if m3u8_content:
        segments = parse_m3u8(m3u8_content, m3u8_url)
        download_segments(segments, segment_path)
        time.sleep(10)
        merge_segments(output_dir, segment_path, output_file)

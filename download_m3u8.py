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


def get_total_segments(m3u8_url):
    """获取m3u8文件中的总片段数，包括处理嵌套的m3u8文件"""
    try:
        import m3u8
        playlist = m3u8.load(m3u8_url)
        
        # 如果是主播放列表（包含子播放列表）
        if playlist.is_endlist and playlist.playlists:
            logger.info("检测到主播放列表，获取子播放列表")
            # 获取第一个子播放列表的URI
            sub_playlist_uri = playlist.playlists[0].uri
            
            # 如果子播放列表URI是相对路径，需要构建完整URL
            if not sub_playlist_uri.startswith('http'):
                from urllib.parse import urljoin
                sub_playlist_uri = urljoin(m3u8_url, sub_playlist_uri)
            
            logger.info(f"加载子播放列表: {sub_playlist_uri}")
            # 递归获取子播放列表的片段数
            return get_total_segments(sub_playlist_uri)
        
        # 如果是包含具体片段的播放列表
        if playlist.segments:
            segment_count = len(playlist.segments)
            logger.info(f"找到 {segment_count} 个媒体片段")
            return segment_count
            
        logger.warning("未找到媒体片段")
        return 0
        
    except Exception as e:
        logger.error(f"获取片段数失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


def execute_ffmpeg(input_url, output_file):
    # 获取总片段数
    total_segments = get_total_segments(input_url)
    logger.info(f"总片段数: {total_segments}")

    # 构建 ffmpeg 命令
    command = [
        'ffmpeg',
        '-i', input_url,
        '-c', 'copy',
        '-progress', 'pipe:1',  # 添加进度输出到 stdout
        output_file
    ]

    try:
        # 执行 ffmpeg 命令并实时获取输出
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # 行缓冲
            universal_newlines=True
        )
        # logger.info(process)
        processed_frames = 0
        # 创建进度文件
        progress_file = os.path.join(output_dir, "progress.txt")

        # 使用非阻塞方式读取输出
        import select

        # 创建轮询对象
        poll = select.poll()
        poll.register(process.stdout, select.POLLIN)
        poll.register(process.stderr, select.POLLIN)

        # 设置初始进度
        with open(progress_file, 'w') as f:
            f.write("0.00")

        while True:
            # 检查是否有新的输出
            for fd, event in poll.poll(100):  # 100ms 超时
                if fd == process.stdout.fileno():
                    line = process.stdout.readline()
                    if line:
                        logger.info(f"stdout: {line.strip()}")
                        if "hls @ " in line:
                            processed_frames += 1
                            # 计算进度百分比
                            progress = (processed_frames / total_segments * 100) if total_segments > 0 else 0
                            # 写入进度到文件
                            with open(progress_file, 'w') as f:
                                f.write(f"{progress:.2f}")
                elif fd == process.stderr.fileno():
                    line = process.stderr.readline()
                    if line:
                        logger.info(f"stderr: {line.strip()}")

            # 检查进程是否结束
            if process.poll() is not None:
                break

        # 读取剩余输出
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(f"剩余 stdout: {stdout}")
        if stderr:
            logger.info(f"剩余 stderr: {stderr}")

        if process.returncode == 0:
            logger.info(f"成功将 {input_url} 转换为 {output_file}")
            # 设置最终进度为 100%
            with open(progress_file, 'w') as f:
                f.write("100.00")
        else:
            logger.error("ffmpeg 命令执行失败")

    except Exception as e:
        logger.error(f"发生了意外错误: {e}")
    finally:
        # 删除进度文件
        if os.path.exists(progress_file):
            os.remove(progress_file)


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

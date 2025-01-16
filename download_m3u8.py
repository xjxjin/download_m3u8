import requests
import subprocess
import os
from urllib.parse import urljoin
import sys
import datetime


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


def download_segments(segments, segment_path):
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
            print(f"下载片段 {i + 1} 完成: {segment_url}")
        except requests.RequestException as e:
            print(f"下载片段 {i + 1} 失败: {e}")


def merge_segments(output_dir, segment_path, output_file):
    segment_files = [os.path.join(segment_path, f) for f in sorted(os.listdir(segment_path)) if
                     f.endswith('.ts')]
    segment_list = f'{segment_path}/segment_list.txt'
    with open(segment_list, 'w') as f:
        for segment_file in segment_files:
            f.write(f"file '{segment_file}'\n")
    try:
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', segment_list,
                        '-c', 'copy', f"{output_dir}/{output_file}"], check=True)
        print(f"合并完成，输出文件: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"合并失败: {e}")
    finally:
        if os.path.exists(segment_list):
            os.remove(segment_list)
        if os.path.exists(segment_path):
            os.remove(segment_path)


if __name__ == "__main__":
    # 从环境变量获取 m3u8_url 和 output_dir
    m3u8_url = os.getenv("M3U8_URL")
    output_dir = os.getenv("OUTPUT_DIR", "downloaded_segments")
    # output_file = "merged_video.mp4"
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_file = f"merged_video_{now}.mp4"
    if not m3u8_url:
        print("请设置环境变量 M3U8_URL")
        sys.exit(1)
    segment_path = f"{output_dir}/tmp/{now}"
    m3u8_content = get_m3u8_content(m3u8_url)
    if m3u8_content:
        segments = parse_m3u8(m3u8_content, m3u8_url)
        download_segments(segments, segment_path)
        merge_segments(output_dir, segment_path, output_file)

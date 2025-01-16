import requests
import subprocess
import os
from urllib.parse import urljoin
import sys


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


def download_segments(segments, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for i, segment_url in enumerate(segments):
        segment_file = os.path.join(output_dir, f"segment_{i}.ts")
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


def merge_segments(output_dir, output_file):
    segment_files = [os.path.join(output_dir, f) for f in sorted(os.listdir(output_dir)) if
                    f.endswith('.ts')]
    with open('segment_list.txt', 'w') as f:
        for segment_file in segment_files:
            f.write(f"file '{segment_file}'\n")
    try:
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i','segment_list.txt',
                      '-c', 'copy', output_file], check=True)
        print(f"合并完成，输出文件: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"合并失败: {e}")
    finally:
        if os.path.exists('segment_list.txt'):
            os.remove('segment_list.txt')


if __name__ == "__main__":
    # 从环境变量获取 m3u8_url 和 output_dir
    m3u8_url = os.getenv("M3U8_URL")
    output_dir = os.getenv("OUTPUT_DIR", "downloaded_segments")
    output_file = "merged_video.mp4"

    if not m3u8_url:
        print("请设置环境变量 M3U8_URL")
        sys.exit(1)

    m3u8_content = get_m3u8_content(m3u8_url)
    if m3u8_content:
        segments = parse_m3u8(m3u8_content, m3u8_url)
        download_segments(segments, output_dir)
        merge_segments(output_dir, output_file)
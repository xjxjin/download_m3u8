# app.py
from flask import Flask, render_template, request, jsonify, send_file
import os
# import requests
# import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
import time
import subprocess
import shutil
import datetime

# import logging
# from logging.handlers import TimedRotatingFileHandler
# from datetime import datetime

app = Flask(__name__)

# 获取download_m3u8.py中定义的output_dir
from download_m3u8 import output_dir, setup_logger

# 使用相同的日志配置
logger = setup_logger()

# 添加全局变量来存储下载进度
download_progress = {
    'progress': 0,
    'current_segments': 0,
    'total_segments': 0,
    'status': 'idle',  # idle, downloading, completed, failed
    'error': None
}


def get_m3u8_url(web_url):
    """使用Selenium模拟手机访问并获取m3u8链接和视频名称"""
    logger.info(f"开始处理URL: {web_url}")
    chrome_options = Options()

    # Docker 环境特定设置
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')

    # 检测运行环境
    is_docker = os.path.exists('/.dockerenv')
    logger.info(f"运行环境: {'Docker' if is_docker else '本地'}")

    if is_docker:
        # Docker 环境使用环境变量中的浏览器
        chrome_bin = os.getenv('CHROME_BIN')
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')

        if not chrome_bin or not os.path.exists(chrome_bin):
            logger.info("Google Chrome 不存在，尝试使用 Chromium")
            chrome_bin = os.getenv('CHROMIUM_BIN')
            chromedriver_path = os.getenv('CHROMIUM_DRIVER_PATH')

        if not chrome_bin or not os.path.exists(chrome_bin):
            logger.error(f"Docker环境中未找到可用的浏览器")
            raise Exception("未找到可用的浏览器")
    else:
        # 本地环境自动检测浏览器
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            import requests.exceptions

            # 尝试查找本地 Chrome 或 Chromium
            if os.path.exists('/usr/bin/google-chrome'):
                chrome_bin = '/usr/bin/google-chrome'
            elif os.path.exists('/usr/bin/chromium'):
                chrome_bin = '/usr/bin/chromium'
            elif os.path.exists('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'):
                chrome_bin = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
            elif os.path.exists('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'):
                chrome_bin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            else:
                chrome_bin = None
                logger.warning("未找到本地Chrome/Chromium，将使用系统默认浏览器")

            # 尝试使用缓存的 ChromeDriver
            cache_path = os.path.join(os.path.expanduser("~"), ".wdm", "drivers.json")
            if os.path.exists(cache_path):
                import json
                try:
                    with open(cache_path, 'r') as f:
                        cache = json.load(f)
                        for driver in cache.get('chrome', {}).values():
                            driver_path = driver.get('binary_path')
                            if driver_path and os.path.exists(driver_path):
                                chromedriver_path = driver_path
                                logger.info(f"使用缓存的ChromeDriver: {chromedriver_path}")
                                break
                except Exception as e:
                    logger.warning(f"读取缓存失败: {str(e)}")

            # 如果没有找到缓存的驱动，尝试下载
            if not locals().get('chromedriver_path'):
                try:
                    chromedriver_path = ChromeDriverManager().install()
                    logger.info(f"下载新的ChromeDriver: {chromedriver_path}")
                except requests.exceptions.ConnectionError:
                    logger.error("网络连接失败，无法下载ChromeDriver")
                    raise Exception("网络连接失败，请检查网络或手动下载ChromeDriver")
                except Exception as e:
                    logger.error(f"下载ChromeDriver失败: {str(e)}")
                    raise

        except Exception as e:
            logger.error(f"本地环境配置失败: {str(e)}")
            raise Exception(f"浏览器配置失败: {str(e)}")

    logger.info(f"使用浏览器: {chrome_bin if chrome_bin else '系统默认'}")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    # 启用性能日志
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # 设置移动设备模拟
    mobile_emulation = {
        "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

    try:
        logger.info(f"使用驱动: {chromedriver_path}")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 启用性能日志
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Performance.enable', {})

        # 访问页面
        logger.info(f"开始访问页面: {web_url}")
        driver.get(web_url)

        # 等待页面加载
        logger.info("等待页面加载...")
        time.sleep(10)

        def check_for_m3u8():
            """检查网络日志中是否有m3u8链接"""
            logs = driver.get_log('performance')
            m3u8_urls = []
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if (
                            'Network.requestWillBeSent' in log['method']
                            and 'm3u8' in log['params']['request']['url'].lower()
                    ):
                        url = log['params']['request']['url']
                        if url.startswith('http') and '.m3u8' in url:
                            logger.info(f"捕获到M3U8链接: {url}")
                            m3u8_urls.append(url)
                except Exception as e:
                    logger.error(f"解析日志时出错: {str(e)}")
                    continue
            return m3u8_urls

        # 第一次检查m3u8链接
        m3u8_urls = check_for_m3u8()

        # 如果没有找到m3u8链接，尝试触发视频播放
        if not m3u8_urls:
            logger.info("未找到M3U8链接，尝试触发视频播放...")
            try:
                # 尝试点击视频播放按钮或视频区域
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                # 常见的视频播放器选择器
                video_selectors = [
                    "video",  # HTML5 视频标签
                    ".video-player",  # 常见的视频播放器类名
                    "#player",  # 播放器ID
                    ".player",  # 播放器类名
                    ".play-button",  # 播放按钮
                    "[class*='play']",  # 包含play的类名
                    "[id*='player']",  # 包含player的ID
                ]

                # 尝试查找并点击视频元素
                for selector in video_selectors:
                    try:
                        element = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"找到视频元素: {selector}")
                        # 尝试点击元素
                        driver.execute_script("arguments[0].click();", element)
                        # 等待可能的m3u8请求
                        time.sleep(3)
                        # 再次检查m3u8链接
                        m3u8_urls = check_for_m3u8()
                        if m3u8_urls:
                            break
                    except Exception as e:
                        logger.debug(f"尝试选择器 {selector} 失败: {str(e)}")
                        continue

                # 如果还是没有找到，尝试执行一些常见的视频初始化函数
                if not m3u8_urls:
                    logger.info("尝试执行视频初始化函数...")
                    init_scripts = [
                        "if(typeof player !== 'undefined') player.play();",
                        "document.querySelector('video')?.play();",
                        "document.querySelector('[class*=\"play\"]')?.click();",
                    ]
                    for script in init_scripts:
                        try:
                            driver.execute_script(script)
                            time.sleep(3)
                            m3u8_urls = check_for_m3u8()
                            if m3u8_urls:
                                break
                        except Exception as e:
                            logger.debug(f"执行脚本失败: {str(e)}")
                            continue

            except Exception as e:
                logger.error(f"触发视频播放失败: {str(e)}")

        # 获取视频标题
        video_title = ""
        try:
            # 获取页面标题作为视频名称
            video_title = driver.title
            # 清理标题中的特殊字符
            import re
            video_title = re.sub(r'[\\/:*?"<>|]', '_', video_title)
            logger.info(f"获取到视频标题: {video_title}")
        except Exception as e:
            logger.error(f"获取视频标题失败: {str(e)}")
            video_title = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # 如果找到了m3u8链接，返回链接和标题
        if m3u8_urls:
            logger.info(f"成功找到M3U8链接: {m3u8_urls[0]}")
            return {'url': m3u8_urls[0], 'title': video_title}

        logger.warning("未找到M3U8链接")
        return None

    except Exception as e:
        logger.error(f"Selenium错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"关闭driver时出错: {str(e)}")
            pass


@app.route('/')
def index():
    logger.info("访问首页")
    return render_template('index.html')


@app.route('/get_m3u8', methods=['POST'])
def get_m3u8():
    web_url = request.json.get('web_url')
    if not web_url:
        logger.warning("未提供网页URL")
        return jsonify({'success': False, 'error': '请输入网页URL'})

    logger.info(f"收到请求，URL: {web_url}")

    try:
        result = get_m3u8_url(web_url)
        if not result:
            return jsonify({'success': False, 'error': '未找到M3U8链接'})
        return jsonify({
            'success': True,
            'm3u8_url': result['url'],
            'video_title': result['title']
        })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取M3U8错误: {error_msg}")
        return jsonify({'success': False, 'error': f'获取M3U8失败: {error_msg}'})


@app.route('/execute', methods=['POST'])
def execute():
    m3u8_url = request.json.get('m3u8_url')
    video_title = request.json.get('video_title', '')

    if not m3u8_url:
        logger.warning("未提供M3U8 URL")
        return jsonify({'success': False, 'error': 'M3U8 URL is required'})

    try:
        logger.info(f"开始下载M3U8: {m3u8_url}")
        logger.info(f"视频标题: {video_title}")

        # 设置环境变量
        os.environ['M3U8_URL'] = m3u8_url
        os.environ['VIDEO_TITLE'] = video_title

        subprocess.run(['python', 'download_m3u8.py'], check=True)
        logger.info("下载完成")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/list_files')
def list_files():
    # 获取路径参数，如果为空则使用默认输出目录
    path = request.args.get('path')
    if not path:
        path = output_dir
        logger.info(f"使用默认输出目录: {path}")

    logger.info(f"列出目录内容: {path}")

    # 确保目录存在
    try:
        # 检查路径是否为空或无效
        if not path or not path.strip():
            logger.error("无效的路径参数")
            return jsonify({'success': False, 'error': '无效的路径参数'})

        # 创建目录
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")
        return jsonify({'success': False, 'error': f'创建目录失败: {str(e)}'})

    try:
        files = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            stats = os.stat(item_path)

            # 获取文件类型
            file_type = '文件夹' if os.path.isdir(item_path) else '文件'

            # 获取文件大小
            size = stats.st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.2f} KB"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.2f} MB"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"

            files.append({
                'name': item,
                'path': item_path,
                'is_dir': os.path.isdir(item_path),
                'type': file_type,
                'size': size_str,
                'created_time': datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'modified_time': datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

        # 按修改时间倒序排序
        files.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)

        return jsonify({
            'success': True,
            'current_path': os.path.abspath(path),
            'files': files
        })
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download/<path:filepath>')
def download_file(filepath):
    logger.info(f"下载文件: {filepath}")
    try:
        # 移除路径中的重复 /app 前缀
        if filepath.startswith('app/'):
            filepath = filepath.replace('app/', '', 1)
            logger.info(f"下载文件1: {filepath}")
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/rename', methods=['POST'])
def rename_file():
    old_path = request.json.get('old_path')
    new_name = request.json.get('new_name')
    if not all([old_path, new_name]):
        logger.warning("重命名参数不完整")
        return jsonify({'success': False, 'error': 'Missing parameters'})

    try:
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        logger.info(f"重命名文件: {old_path} -> {new_path}")
        os.rename(old_path, new_path)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"重命名失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/move', methods=['POST'])
def move_file():
    source = request.json.get('source')
    destination = request.json.get('destination')
    if not all([source, destination]):
        logger.warning("移动文件参数不完整")
        return jsonify({'success': False, 'error': 'Missing parameters'})

    try:
        logger.info(f"移动文件: {source} -> {destination}")
        shutil.move(source, destination)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"移动文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/delete', methods=['POST'])
def delete_file():
    filepath = request.json.get('filepath')
    if not filepath:
        logger.warning("删除文件参数不完整")
        return jsonify({'success': False, 'error': 'Missing filepath'})

    try:
        logger.info(f"删除文件: {filepath}")
        if os.path.isdir(filepath):
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/check_progress')
def check_progress():
    return jsonify({
        'success': True,
        'progress': download_progress['progress'],
        'current_segments': download_progress['current_segments'],
        'total_segments': download_progress['total_segments'],
        'status': download_progress['status'],
        'error': download_progress['error']
    })


if __name__ == '__main__':
    logger.info("启动应用服务器，监听端口: 5020")
    app.run(host='0.0.0.0', port=5020)

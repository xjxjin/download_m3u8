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
# import logging
# from logging.handlers import TimedRotatingFileHandler
# from datetime import datetime

app = Flask(__name__)

# 获取download_m3u8.py中定义的output_dir
from download_m3u8 import output_dir, setup_logger

# 使用相同的日志配置
logger = setup_logger()

def get_m3u8_url(web_url):
    """使用Selenium模拟手机访问并获取m3u8链接"""
    logger.info(f"开始处理URL: {web_url}")
    chrome_options = Options()
    
    # Docker 环境特定设置
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # 尝试使用 Google Chrome，如果失败则使用 Chromium
    chrome_bin = os.getenv('CHROME_BIN')
    chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
    
    if not os.path.exists(chrome_bin):
        logger.info("Google Chrome 不存在，尝试使用 Chromium")
        chrome_bin = os.getenv('CHROMIUM_BIN')
        chromedriver_path = os.getenv('CHROMIUM_DRIVER_PATH')
    
    if not os.path.exists(chrome_bin):
        raise Exception("未找到可用的浏览器")
    
    chrome_options.binary_location = chrome_bin
    
    # 启用性能日志
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    # 设置移动设备模拟
    mobile_emulation = {
        "deviceMetrics": { "width": 375, "height": 812, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    try:
        logger.info(f"使用浏览器: {chrome_bin}")
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
        
        # 获取所有网络请求
        logs = driver.get_log('performance')
        m3u8_urls = []
        
        import json
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                if (
                    'Network.requestWillBeSent' in log['method']
                    and 'm3u8' in log['params']['request']['url'].lower()
                ):
                    url = log['params']['request']['url']
                    logger.info(f"捕获到M3U8链接: {url}")
                    m3u8_urls.append(url)
            except Exception as e:
                logger.error(f"解析日志时出错: {str(e)}")
                continue
        
        # 如果找到了m3u8链接，返回第一个
        if m3u8_urls:
            logger.info(f"成功找到M3U8链接: {m3u8_urls[0]}")
            return m3u8_urls[0]
        
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
        m3u8_url = get_m3u8_url(web_url)
        if not m3u8_url:
            return jsonify({'success': False, 'error': '未找到M3U8链接'})
        return jsonify({'success': True, 'm3u8_url': m3u8_url})
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取M3U8错误: {error_msg}")
        return jsonify({'success': False, 'error': f'获取M3U8失败: {error_msg}'})

@app.route('/execute', methods=['POST'])
def execute():
    m3u8_url = request.json.get('m3u8_url')
    if not m3u8_url:
        logger.warning("未提供M3U8 URL")
        return jsonify({'success': False, 'error': 'M3U8 URL is required'})
    
    try:
        logger.info(f"开始下载M3U8: {m3u8_url}")
        os.environ['M3U8_URL'] = m3u8_url
        subprocess  .run(['python', 'download_m3u8.py'], check=True)
        logger.info("下载完成")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/list_files')
def list_files():
    path = request.args.get('path', output_dir)
    logger.info(f"列出目录内容: {path}")
    if not os.path.exists(path):
        logger.warning(f"路径不存在: {path}")
        return jsonify({'success': False, 'error': 'Path does not exist'})
    
    try:
        files = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            files.append({
                'name': item,
                'path': item_path,
                'is_dir': os.path.isdir(item_path),
                'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0
            })
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<path:filepath>')
def download_file(filepath):
    logger.info(f"下载文件: {filepath}")
    try:
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

if __name__ == '__main__':
    logger.info("启动应用服务器，监听端口: 5020")
    app.run(host='0.0.0.0', port=5020)
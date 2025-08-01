import requests
import logging

def webhook_p(old_ip, new_ip,webhook,now_time,if_post):
    
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler("log.txt")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    content = "当前公网IP地址为:" + new_ip + "\n上一个公网IP地址为:" + old_ip + "\n当前时间为:" + now_time + "\n通知结果:" + if_post
    
    try:
        response = requests.post(
            webhook,
            json=content,
            timeout=5  # 设置超时时间（秒）
        )
        logger.info(f"状态码: {response.status_code}")
        logger.info(f"响应: {response.json()}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: {e}")
        logger.error("请确保Flask应用正在运行且端口未被占用。")
    except Exception as e:
        logger.error(f"其他错误: {e}")


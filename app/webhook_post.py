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
    
    # 将content改为字典格式
    content = {
        "current_ip": new_ip,
        "previous_ip": old_ip,
        "timestamp": now_time,
        "notification_result": if_post
    }
    
    try:
        response = requests.post(
            webhook,
            json=content,  # 现在传递的是字典
            timeout=5  # 设置超时时间（秒）
        )
        logger.info(f"状态码: {response.status_code}")
        logger.info(f"响应: {response.json()}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: {e}")
        logger.error("请确保Flask应用正在运行且端口未被占用。")
    except Exception as e:
        logger.error(f"其他错误: {e}")


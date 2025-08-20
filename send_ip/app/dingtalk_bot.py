from dingtalkchatbot.chatbot import DingtalkChatbot
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import json


def test_dingtalk_connection(webhook, secret):
    """钉钉测试：不发送消息，通过错误码判断有效性"""
    try:
        # 生成签名（与官方SDK一致）
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{secret}'.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        # 处理已有参数的URL
        separator = "&" if "?" in webhook else "?"
        url = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
        
        # 发送无效请求（缺少msgtype）
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"invalid_key": "invalid_value"}  # 故意错误的格式
        
        response = requests.post(
            url=url,
            data=json.dumps(payload),
            headers=headers,
            timeout=8
        )
        
        # 有效钉钉机器人会返回200状态码，且errcode为参数错误类
        response_json = response.json()
        valid_codes = {300001, 40001, 40013}  # 兼容多种参数错误码
        return response.status_code == 200 and response_json.get("errcode") in valid_codes
        
    except:
        return False


def dingtalk_robot(old_ip, new_ip, webhook, secret, at_all, now_time, if_post):
    """钉钉发送函数：确保格式正确"""
    try:
        if_post = if_post.lstrip('\n')
        lines = if_post.splitlines()
        bold_lines = [f"**{line}**" for line in lines]
        markdown_output = "  \n".join(bold_lines)
        
        dingding_bot = DingtalkChatbot(webhook, secret)
        dingding_bot.send_markdown(
            title='公网IP变动说明',
            text=f'### **当前公网IP地址为:{new_ip}**\n'  
                f'### **上一个公网IP地址为:{old_ip}**\n'
                f'**发送时间:  {now_time}**\n\n'
                f'**通知结果:**  \n\n'
                f'{markdown_output}\n',
            is_at_all=at_all
        )
        return True
    except Exception as e:
        raise Exception(f"钉钉发送失败: {str(e)}")

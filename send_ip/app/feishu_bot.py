import requests
import json


def test_feishu_connection(webhook):
    """根据实际日志定制：只判断有效机器人，排除错误token和无效URL"""
    try:
        # 1. 严格域名检查（仅允许飞书官方域名）
        valid_domains = ["open.feishu.cn", "open.larksuite.com"]
        if not any(domain in webhook for domain in valid_domains):
            print(f"飞书检测失败：非官方域名 (webhook: {webhook[:30]}...)")
            return False
        
        # 2. 发送测试请求（无效格式，不产生消息）
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"invalid_key": "invalid_value"}  # 故意缺少msg_type
        
        response = requests.post(
            url=webhook,
            data=json.dumps(payload),
            headers=headers,
            timeout=10
        )
        
        # 3. 根据你的日志结果定制判断逻辑：
        # - 状态码200 + code=19002 → 有效（参数错误，机器人存在）
        # - 状态码200 + code=19001 → 无效（token错误）
        # - 其他情况 → 无效
        if response.status_code != 200:
            print(f"飞书检测失败：状态码非200 ({response.status_code})")
            return False
            
        try:
            response_json = response.json()
            code = response_json.get("code")
            
            if code == 19002:
                print("飞书检测通过：有效机器人（参数错误，正常现象）")
                return True
            elif code == 19001:
                print("飞书检测失败：webhook token无效（code=19001）")
                return False
            else:
                print(f"飞书检测失败：未知错误码 ({code})")
                return False
                
        except:
            print("飞书检测失败：响应不是JSON（非飞书机器人）")
            return False
            
    except Exception as e:
        print(f"飞书检测失败：请求异常 ({str(e)})")
        return False


def sendfeishu(old_ip, new_ip, webhook, now_time, if_post, user_id='', all_user=False):
    # 发送函数保持不变（已确认可正常工作）
    try:
        url = webhook
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        at_user = f"<at user_id=\"{user_id}\"></at>" if user_id else ""
        at_all = "<at user_id=\"all\"></at>" if all_user == 'True' else ""
        
        content = (
            f"当前公网IP地址为: {new_ip}\n"
            f"上一个公网IP地址为: {old_ip}\n"
            f"当前时间为: {now_time}\n"
            f"通知结果: {if_post}"
        )
        
        payload = {
            "msg_type": "text",
            "content": {"text": content + at_user + at_all}
        }
        
        response = requests.post(
            url=url,
            data=json.dumps(payload),
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        response_json = response.json()
        if response_json.get("code") != 0:
            raise Exception(f"飞书API错误: {response_json}")
        
        return True
    except Exception as e:
        raise Exception(f"飞书发送失败: {str(e)}")

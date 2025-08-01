import requests
import json
import time


def sendfeishu(old_ip, new_ip,webhook,now_time,if_post,user_id='',all_user=False):

    class FeishuTalk:
        
        # 机器人webhook
        chatGPT_url = webhook
        
        # 发送文本消息
        def sendTextmessage(self, content):
            at_user = ''
            at_all = ''
            
            if user_id != '':               
                at_user = f"<at user_id=\"{user_id}\">test</at>"  
            
            if all_user == 'True':
                at_all = "<at user_id=\"all\">test</at>"

            
            url = self.chatGPT_url
            headers = {
                "Content-Type": "application/json; charset=utf-8",
            }
            payload_message = {
                "msg_type": "text",
                "content": {
                	# @ 单个用户 <at user_id="ou_xxx">名字</at>
                    "text": content + at_user + at_all
                    # @ 所有人 <at user_id="all">所有人</at>
                    # "text": content + "<at user_id=\"all\">test</at>"
                }
            }
            response = requests.post(url=url, data=json.dumps(payload_message), headers=headers)
            return response.json
    

    # 执行发送文本消息
    content = "当前公网IP地址为:" + new_ip + "\n上一个公网IP地址为:" + old_ip + "\n当前时间为:" + now_time + "\n通知结果:" + if_post
    FeishuTalk().sendTextmessage(content)
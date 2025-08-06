from dingtalkchatbot.chatbot import DingtalkChatbot


def dingtalk_robot(old_ip, new_ip,webhook,secret,at_all,now_time,if_post):
    dingding_bot = DingtalkChatbot(webhook, secret)

    dingding_bot.send_markdown(
        title=f'公网IP变动说明',
        text=f'### **当前公网IP地址为:{new_ip}**\n'  
            f'### **上一个公网IP地址为:{old_ip}**\n'
            f'**发送时间:  {now_time}**\n\n'
            f'**通知结果:  {if_post}**\n\n',
        is_at_all=at_all)

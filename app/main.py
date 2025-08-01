#!/usr/bin/python3
# -*- coding: utf-8 -*-

import configparser
import time
import logging
from datetime import datetime
from get_ip import getip
from feishu_bot import sendfeishu
from send_email import mail
from dingtalk_bot import dingtalk_robot
from webhook_post import webhook_p

def send_message():
    
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler("app/log.txt")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # 获取配置文件
    file = 'app/config.ini'

    # 创建配置文件对象
    con = configparser.ConfigParser()
    # 读取文件
    con.read(file, encoding='utf-8')

    # 获取特定section
    feishu = con.items('feishu')# 返回结果为元组
    dingtalk = con.items('dingtalk')
    webhook = con.items('webhook')
    email = con.items('email')
    slp_time = con.items('time')


    # 可以通过dict方法转换为字典
    feishu = dict(feishu)
    dingtalk = dict(dingtalk)
    webhook = dict(webhook)
    email = dict(email)
    slp_time = dict(slp_time)

    
    # 推送消息
    with open('app/ip.txt', 'r') as file: 
        old_ip = file.read()
    
    new_ip = getip()
    
    if new_ip == 'null':
        logger.error("当前获取公网IP失败!!!")

    else:
        # 获取上一个IP和当前IP值
        if new_ip != old_ip:
            with open('app/ip.txt', 'w') as file: 
                file.write(new_ip)
            
            now_time = datetime.now().strftime('%Y.%m.%d %H:%M:%S')
            
            if_post = " 飞书:" + feishu['if_post'] + " 钉钉:" + dingtalk['if_post'] + " 邮箱:" + email['if_post'] + " webhook:" + webhook['if_post']
            
            # 执行发送文本消息
            if feishu['if_post'] == 'True':
                try:
                    sendfeishu(old_ip,new_ip,feishu['webhook'],now_time,if_post,feishu['user_id'],feishu["all_user"])
                    logger.info("成功向飞书群发送信息!!!")
                except:
                    logger.error("向飞书群发送信息失败!!!")
            if dingtalk['if_post'] == 'True':
                try:
                    dingtalk_robot(old_ip,new_ip,dingtalk['webhook'],dingtalk['secret'],dingtalk['at_all'],now_time,if_post)
                    logger.info("成功向钉钉群发送信息!!!")
                except:
                    logger.error("向钉钉发送信息失败!!!")
            if email['if_post'] == 'True':
                try:
                    mail(old_ip,new_ip,email["sender_email"],email["sender_pass"],email["receiver_email"],email["smtp_host"],email["smtp_port"],now_time,if_post)
                    logger.info("成功向邮箱发送信息!!!")
                except:
                    logger.error("向邮箱发送信息失败!!!")
            if webhook['if_post'] == 'True':
                for i in webhook.values():
                    webhook_p(old_ip,new_ip,i,now_time,if_post)
                    
    print(f"sleep {slp_time["sleeptime"]} seconds")
    time.sleep(int(slp_time["sleeptime"]))


while True:
    send_message()

    
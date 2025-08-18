#!/usr/bin/python3
# -*- coding: utf-8 -*-

import configparser
import time
import logging
from datetime import datetime
from .get_ip import getip
from .feishu_bot import sendfeishu, test_feishu_connection
from .send_email import mail, test_email_connection
from .dingtalk_bot import dingtalk_robot, test_dingtalk_connection
from .webhook_post import webhook_p, test_webhook_connection

# 添加ASGI相关依赖
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# 创建FastAPI应用
app = FastAPI()
scheduler = AsyncIOScheduler()

# 保留原send_message函数，但改为异步
async def send_message():
    # 配置读取、日志设置等逻辑保持不变...
    file = '.env'
    con = configparser.ConfigParser()
    con.read(file, encoding='utf-8')

    feishu = dict(con.items('feishu'))
    dingtalk = dict(con.items('dingtalk'))
    webhook = dict(con.items('webhook'))
    email = dict(con.items('email'))
    slp_time = dict(con.items('time'))
    file_name = dict(con.items('file_name'))
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(file_name['log_file'])
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # IP获取与更新逻辑保持不变...
    old_ip = ''
    try:
        with open(file_name['ip_file'], 'r') as f:
            old_ip = f.read().strip()
    except:
        logger.info("未找到IP文件，初始化为空")
    
    new_ip = getip()
    current_file_ip = ''
    try:
        with open(file_name['ip_file'], 'r') as f:
            current_file_ip = f.read().strip()
    except:
        pass
    if current_file_ip and current_file_ip != old_ip:
        new_ip = current_file_ip
    
    if new_ip == 'null':
        logger.error("获取公网IP失败")
    else:
        if new_ip != old_ip:
            with open(file_name['ip_file'], 'w') as f:
                f.write(new_ip)
            
            now_time = datetime.now().strftime('%Y.%m.%d %H:%M:%S')
            
            # 飞书测试（无消息）
            feishu_available = test_feishu_connection(feishu['webhook'])
            logger.info(f"飞书检测结果: {'可用' if feishu_available else '不可用'}")
            feishu['if_post'] = 'True' if feishu_available else 'False'
            
            # 钉钉测试（无消息）
            dingtalk_available = test_dingtalk_connection(dingtalk['webhook'], dingtalk['secret'])
            logger.info(f"钉钉检测结果: {'可用' if dingtalk_available else '不可用'}")
            dingtalk['if_post'] = 'True' if dingtalk_available else 'False'
            
            # 在邮件检测部分修改
            # 注意：smtp_port需要转为整数（配置文件可能读为字符串）
            email_available, email_msg = test_email_connection(
                email["sender_email"], 
                email["sender_pass"], 
                email["smtp_host"], 
                int(email["smtp_port"])  # 关键：端口必须为整数
            )
            logger.info(f"邮件检测结果: {'可用' if email_available else '不可用'} ({email_msg})")
            email['if_post'] = 'True' if email_available else 'False'
            
            # 在检测部分添加
            if 'webhook1' in webhook:  # 仅当存在webhook1时检测
                secret_key = webhook.get('secret_key', '')
                webhook_available, webhook_msg = test_webhook_connection(webhook['webhook1'], secret_key if secret_key else None)
                logger.info(f"Webhook检测结果: {'可用' if webhook_available else '不可用'} ({webhook_msg})")
                webhook['if_post'] = 'True' if webhook_available else 'False'

            if_post = ''

            if feishu['webhook'] != '':
                if_post = if_post + f"\n    飞书: {feishu['if_post']}"
            if dingtalk['webhook'] != '':
                if_post = if_post + f"\n    钉钉: {dingtalk['if_post']}"
            if email['sender_email'] != '':
                if_post = if_post + f"\n    邮箱: {email['if_post']}"
            if webhook['webhook1'] != '':
                if_post = if_post + f"\n    webhook: {webhook['if_post']}"
            
            
            if feishu['if_post'] == 'True':
                try:
                    sendfeishu(old_ip, new_ip, feishu['webhook'], now_time, if_post, feishu['user_id'], feishu["all_user"])
                    logger.info("飞书消息发送成功")
                except Exception as e:
                    logger.error(f"飞书发送失败: {str(e)}")
            
            if dingtalk['if_post'] == 'True':
                try:
                    dingtalk_robot(old_ip, new_ip, dingtalk['webhook'], dingtalk['secret'], dingtalk['at_all'], now_time, if_post)
                    logger.info("钉钉消息发送成功")
                except Exception as e:
                    logger.error(f"钉钉发送失败: {str(e)}")


            # 在发送邮件部分修改（捕获详细错误）
            if email['if_post'] == 'True':
                try:
                    send_success, send_msg = mail(
                        old_ip, new_ip, email["sender_email"], email["sender_pass"],
                        email["receiver_email"], email["smtp_host"], int(email["smtp_port"]),
                        now_time, if_post
                    )
                    if send_success:
                        logger.info(f"邮箱消息发送成功: {send_msg}")
                    else:
                        logger.error(f"邮箱消息发送失败: {send_msg}")
                except Exception as e:
                    logger.error(f"邮箱发送逻辑异常: {str(e)}")
            
            
            
            
            
            if webhook['if_post'] == 'True' and 'webhook1' in webhook:
                secret_key = webhook.get('secret_key', '')
                webhook_p(old_ip, new_ip, webhook['webhook1'], now_time, if_post, secret_key if secret_key else None)
    
    print(f"休眠 {slp_time['sleeptime']} 秒")
    # 将time.sleep改为异步等待
    await asyncio.sleep(int(slp_time["sleeptime"]))

# 应用启动时添加定时任务
@app.on_event('startup')
def startup_event():
    # 从配置读取休眠时间 (假设配置文件中有此设置)
    config = configparser.ConfigParser()
    config.read('.env', encoding='utf')
    sleep_time = int(config.get('time', 'sleeptime', fallback=3600))
    
    # 添加定时任务，每隔指定时间执行一次
    scheduler.add_job(send_message, 'interval', seconds=sleep_time)
    scheduler.start()

# 添加健康检查接口
@app.get('/')
def health_check():
    return {"status": "running"}

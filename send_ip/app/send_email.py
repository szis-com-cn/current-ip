import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def mail(old_ip, new_ip, sender_email, sender_pass, receiver_email, smtp_host, smtp_port,now_time,if_post):
    ret = True
    content = "当前公网IP地址为:" + new_ip + "\n上一个公网IP地址为:" + old_ip + "\n当前时间为:" + now_time + "\n通知结果:" + if_post
    
    try:
        msg = MIMEText(content)  # 填写邮件内容
        msg['From'] = formataddr(["Python Bot", sender_email])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr(["Receiver", receiver_email])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject'] = "公网IP变动"  # 邮件的主题，也可以说是标题

        server = smtplib.SMTP_SSL(smtp_host, smtp_port)  # 发件人邮箱中的SMTP服务器
        server.login(sender_email, sender_pass)  # 括号中对应的是发件人邮箱账号、邮箱授权码
        server.sendmail(sender_email, [receiver_email, ], msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
    except Exception:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        ret = False
    return ret


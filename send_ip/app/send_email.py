import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def test_email_connection(sender_email, sender_pass, smtp_host, smtp_port):
    """仅验证SMTP连接和登录，不发送任何邮件"""
    server = None
    try:
        # 连接服务器（支持SSL和STARTTLS）
        if smtp_port == 465:
            # 465端口直接使用SSL
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            # 其他端口（如587）使用STARTTLS加密
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()  # 启用TLS加密
        
        # 验证登录（核心验证步骤）
        server.login(sender_email, sender_pass)
        
        # 无需发送邮件，登录成功即说明配置基本有效
        return True, "连接和登录验证成功"
        
    except smtplib.SMTPAuthenticationError:
        return False, "认证失败：邮箱账号或密码错误"
    except smtplib.SMTPConnectError:
        return False, f"连接失败：无法连接到 {smtp_host}:{smtp_port}"
    except smtplib.SMTPNotSupportedError:
        return False, "服务器不支持SSL/STARTTLS加密"
    except Exception as e:
        return False, f"验证失败：{str(e)}"
    finally:
        # 确保服务器连接关闭
        if server:
            try:
                server.quit()
            except:
                pass


def mail(old_ip, new_ip, sender_email, sender_pass, receiver_email, smtp_host, smtp_port, now_time, if_post):
    """发送邮件函数，增加详细错误日志"""
    content = (
        f"当前公网IP地址为: {new_ip}\n"
        f"上一个公网IP地址为: {old_ip}\n"
        f"当前时间为: {now_time}\n"
        f"通知结果: {if_post}"
    )
    
    try:
        # 构建邮件（确保主题和内容非空，避免被服务器拒绝）
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = formataddr(["IP变动通知", sender_email])  # 昵称避免为空
        msg['To'] = formataddr(["收件人", receiver_email])
        msg['Subject'] = "公网IP变动通知"  # 主题必须非空
        
        # 连接服务器（与检测函数逻辑保持一致，避免加密方式不匹配）
        server = None
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        
        server.login(sender_email, sender_pass)
        # 发送邮件（捕获收件人错误）
        server.sendmail(sender_email, [receiver_email], msg.as_string())
        server.quit()
        return True, "发送成功"
        
    except smtplib.SMTPRecipientsRefused:
        return False, "收件人地址被拒绝（可能无效或被拦截）"
    except smtplib.SMTPDataError as e:
        return False, f"服务器拒绝发送：{e.smtp_code} {e.smtp_error.decode()}"
    except Exception as e:
        return False, f"发送失败：{str(e)}"
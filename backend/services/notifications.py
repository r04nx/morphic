"""Notification services for Morphic backend"""
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional


class NotificationService:
    """Base class for notification services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.destination = config.get('destination', '')
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        """Send alert notification"""
        if not self.enabled or not self.destination:
            return False
        return False


class NtfyService(NotificationService):
    """NTFY notification service"""
    
    def test_connection(self) -> bool:
        """Test NTFY connection"""
        if not self.destination:
            return False
        
        try:
            # Extract topic name (remove URL if present)
            topic = self.destination.split('/')[-1] if '/' in self.destination else self.destination
            
            # Test by publishing a simple test message
            headers = {
                "Title": "Morphic Monitor Connection Test",
                "Priority": "default",
                "Tags": "white_check_mark"
            }
            
            url = f"https://ntfy.sh/{topic}"
            response = requests.post(url, headers=headers, data="Connection test successful!", timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"NTFY connection test successful for topic: {topic}")
                return True
            else:
                print(f"NTFY connection test failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"NTFY connection test failed: {e}")
            return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            priority = "high" if status in ["DOWN", "CRITICAL"] else "default"
            tags = {
                "UP": "white_check_mark",
                "DOWN": "x", 
                "DEGRADED": "warning",
                "CRITICAL": "rotating_light"
            }.get(status, "information_source")
            
            # Extract topic name (remove URL if present)
            topic = self.destination.split('/')[-1] if '/' in self.destination else self.destination
            
            # Use NTFY headers instead of JSON payload
            headers = {
                "Title": f"Monitor Alert: {monitor_id}",
                "Priority": priority,
                "Tags": tags,
                "Click": f"http://localhost:3000/monitors/{monitor_id}"
            }
            
            url = f"https://ntfy.sh/{topic}"
            
            response = requests.post(url, headers=headers, data=f"Status: {status}\n{message}", timeout=10)
            print(f"NTFY response: {response.status_code} - {response.text}")
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"NTFY notification failed: {e}")
            return False


class EmailService(NotificationService):
    """Email notification service"""
    
    def __init__(self, config, settings_manager=None):
        super().__init__(config)
        self.settings_manager = settings_manager
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        if not self.settings_manager:
            return False
            
        smtp_settings = self.settings_manager.get_setting('smtp', {})
        
        if not smtp_settings.get('enabled') or not smtp_settings.get('host'):
            return False
        
        try:
            import smtplib
            
            server = smtplib.SMTP(smtp_settings['host'], smtp_settings.get('port', 587), timeout=10)
            server.ehlo()
            
            if smtp_settings.get('use_tls', True):
                server.starttls()
                server.ehlo()
            
            if smtp_settings.get('username') and smtp_settings.get('password'):
                # Remove spaces from app password if present
                password = smtp_settings['password'].replace(' ', '')
                server.login(smtp_settings['username'], password)
            
            server.quit()
            print(f"SMTP connection test successful to {smtp_settings['host']}")
            return True
            
        except Exception as e:
            print(f"SMTP connection test failed: {e}")
            return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            # Get SMTP settings from global settings
            smtp_settings = {}
            if self.settings_manager:
                smtp_settings = self.settings_manager.get_setting('smtp', {})
            
            subject = f"Monitor Alert: {monitor_id} is {status}"
            body = f"""
Monitor: {monitor_id}
Status: {status}
Time: {datetime.now().isoformat()}
Message: {message}

View details: http://localhost:3000/monitors/{monitorId}
            """
            
            if smtp_settings.get('enabled') and smtp_settings.get('host'):
                # Real SMTP implementation
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart()
                msg['From'] = smtp_settings.get('from_email', 'noreply@morphic.dev')
                msg['To'] = self.destination
                msg['Subject'] = subject
                
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(smtp_settings['host'], smtp_settings.get('port', 587))
                server.ehlo()
                if smtp_settings.get('use_tls', True):
                    server.starttls()
                    server.ehlo()
                if smtp_settings.get('username') and smtp_settings.get('password'):
                    password = smtp_settings['password'].replace(' ', '')
                    server.login(smtp_settings['username'], password)
                
                server.send_message(msg)
                server.quit()
                
                print(f"Email sent to {self.destination} via SMTP")
                return True
            else:
                # Mock implementation when SMTP not configured
                print(f"EMAIL TO: {self.destination}")
                print(f"SUBJECT: {subject}")
                print(f"BODY: {body}")
                print("(SMTP not configured - using mock implementation)")
                return True
                
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False


class TelegramService(NotificationService):
    """Telegram notification service"""
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        bot_token = self.config.get('bot_token')
        if not bot_token:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    print(f"Telegram bot connection successful: @{bot_info['result']['username']}")
                    return True
            
            print(f"Telegram bot connection failed: {response.text}")
            return False
            
        except Exception as e:
            print(f"Telegram connection test failed: {e}")
            return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            bot_token = self.config.get('bot_token')
            if not bot_token:
                return False
            
            # Extract chat ID from webhook URL or use directly
            chat_id = self.destination
            if self.destination.startswith('https'):
                # Extract from webhook URL format
                chat_id = self.destination.split('/')[-1] if '/' in self.destination else self.destination
            
            emoji = {
                "UP": "✅",
                "DOWN": "❌", 
                "DEGRADED": "⚠️",
                "CRITICAL": "🚨"
            }.get(status, "ℹ️")
            
            text = f"{emoji} *Monitor Alert*\n"
            text += f"Monitor: `{monitor_id}`\n"
            text += f"Status: `{status}`\n"
            text += f"Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            text += f"\n{message}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False


class SlackService(NotificationService):
    """Slack notification service"""
    
    def test_connection(self) -> bool:
        """Test Slack webhook connection"""
        bot_token = self.config.get('bot_token')
        if not bot_token:
            return False
        
        try:
            url = f"https://hooks.slack.com/services/{bot_token}"
            test_payload = {
                "text": "Morphic Monitor Connection Test",
                "username": "Morphic Monitor",
                "icon_emoji": ":robot_face:"
            }
            
            response = requests.post(url, json=test_payload, timeout=10)
            
            if response.status_code == 200:
                print("Slack webhook connection successful")
                return True
            else:
                print(f"Slack webhook connection failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Slack connection test failed: {e}")
            return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            bot_token = self.config.get('bot_token')
            if not bot_token:
                return False
            
            emoji = {
                "UP": ":white_check_mark:",
                "DOWN": ":x:", 
                "DEGRADED": ":warning:",
                "CRITICAL": ":rotating_light:"
            }.get(status, ":information_source:")
            
            color = {
                "UP": "good",
                "DOWN": "danger", 
                "DEGRADED": "warning",
                "CRITICAL": "danger"
            }.get(status, "good")
            
            payload = {
                "channel": self.destination,
                "username": "Morphic Monitor",
                "icon_emoji": ":robot_face:",
                "attachments": [{
                    "color": color,
                    "title": f"{emoji} Monitor Alert: {monitor_id}",
                    "text": message,
                    "fields": [
                        {
                            "title": "Status",
                            "value": status,
                            "short": True
                        },
                        {
                            "title": "Time", 
                            "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "actions": [{
                        "type": "button",
                        "text": "View Details",
                        "url": f"http://localhost:3000/monitors/{monitor_id}"
                    }]
                }]
            }
            
            url = f"https://hooks.slack.com/services/{bot_token}"
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Slack notification failed: {e}")
            return False


class NotificationManager:
    """Manages all notification services"""
    
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.services = {
            'NTFY': NtfyService,
            'EMAIL': EmailService, 
            'TELEGRAM': TelegramService,
            'SLACK': SlackService
        }
    
    def create_service(self, notification_type: str, config: Dict[str, Any]) -> NotificationService:
        """Create notification service instance"""
        service_class = self.services.get(notification_type, NotificationService)
        
        # Pass settings_manager to EmailService
        if notification_type == 'EMAIL':
            return service_class(config, self.settings_manager)
        else:
            return service_class(config)
    
    def send_alerts(self, monitor_id: str, notifications: list, status: str, message: str, **kwargs) -> Dict[str, bool]:
        """Send alerts to all configured notification channels"""
        results = {}
        
        for notification in notifications:
            if not notification.get('enabled', False):
                continue
                
            notification_type = notification.get('type')
            if not notification_type:
                continue
            
            service = self.create_service(notification_type, notification)
            success = service.send_alert(monitor_id, status, message, **kwargs)
            results[notification_type] = success
        
        return results

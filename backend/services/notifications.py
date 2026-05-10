"""Notification services for Morphic backend"""
import requests
import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

MORPHIC_LOGO_PNG_BASE64 = "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"


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
    """Email notification service using SMTP"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_from = os.getenv('EMAIL_FROM', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            if not all([self.smtp_host, self.email_from, self.email_password]):
                print("Email service test failed: Missing SMTP configuration")
                return False
            
            # Test connection to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.email_from, self.email_password)
            server.quit()
            
            print("SMTP connection test successful")
            return True
            
        except Exception as e:
            print(f"SMTP connection test failed: {e}")
            return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            if not all([self.smtp_host, self.email_from, self.email_password]):
                print("Email sending failed: Missing SMTP configuration")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.destination
            msg['Subject'] = f"Monitor Alert: {monitor_id} - {status}"
            
            # Create HTML email body
            status_bg = '#e5e7eb'
            status_fg = '#111827'
            status_border = '#d1d5db'
            if status in ['DOWN', 'CRITICAL']:
                status_bg = '#fee2e2'
                status_fg = '#991b1b'
                status_border = '#fecaca'
            elif status == 'DEGRADED':
                status_bg = '#fef3c7'
                status_fg = '#92400e'
                status_border = '#fde68a'

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            details_url = f"http://localhost:3000/monitors/{monitor_id}"

            html_body = f"""
            <html>
            <body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
              <div style="max-width:680px;margin:24px auto;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
                <div style="background-color:#111827;color:#ffffff;padding:18px 20px;">
                  <table style="width:100%;border-collapse:collapse;">
                    <tr>
                      <td style="width:44px;vertical-align:middle;">
                        <img alt="Morphic" width="32" height="32" style="display:block;border-radius:6px;" src="data:image/png;base64,{MORPHIC_LOGO_PNG_BASE64}" />
                      </td>
                      <td style="vertical-align:middle;text-align:left;">
                        <div style="font-size:14px;letter-spacing:0.3px;font-weight:600;line-height:18px;">Morphic</div>
                        <div style="font-size:12px;opacity:0.85;line-height:16px;">Monitor Notification</div>
                      </td>
                    </tr>
                  </table>
                </div>

                <div style="padding:18px 20px;text-align:left;">
                  <div style="display:inline-block;padding:6px 10px;border-radius:999px;background:{status_bg};color:{status_fg};border:1px solid {status_border};font-size:12px;font-weight:600;letter-spacing:0.6px;text-transform:uppercase;">
                    {status}
                  </div>

                  <h2 style="margin:14px 0 10px 0;font-size:16px;line-height:22px;color:#111827;">Monitor status change detected</h2>

                  <table style="width:100%;border-collapse:collapse;margin:0 0 14px 0;">
                    <tr>
                      <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Monitor ID</td>
                      <td style="padding:8px 0;color:#111827;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;">{monitor_id}</td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Timestamp</td>
                      <td style="padding:8px 0;color:#111827;font-size:12px;">{now_str}</td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Dashboard</td>
                      <td style="padding:8px 0;color:#111827;font-size:12px;">
                        <a href="{details_url}" style="color:#111827;text-decoration:underline;">{details_url}</a>
                      </td>
                    </tr>
                  </table>

                  <div style="border:1px solid #e5e7eb;background-color:#f9fafb;border-radius:10px;padding:12px 12px;">
                    <div style="color:#6b7280;font-size:12px;font-weight:600;margin-bottom:6px;">Message</div>
                    <div style="color:#111827;font-size:13px;line-height:18px;white-space:pre-wrap;">{message}</div>
                  </div>
                </div>

                <div style="border-top:1px solid #e5e7eb;background-color:#ffffff;padding:14px 20px;text-align:left;">
                  <div style="color:#6b7280;font-size:11px;line-height:16px;">
                    You are receiving this because email alerts are enabled for this monitor.
                  </div>
                </div>
              </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.email_from, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_from, self.destination, text)
            server.quit()
            
            print(f"Email alert sent successfully to {self.destination}")
            return True
            
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False


_telegram_pending_verifications: Dict[str, str] = {}

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


class TelegramService(NotificationService):
    """Telegram notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.destination = config.get('destination')
        self.verification_code = None
        self.verified_chat_id = None

    def _get_bot_token(self) -> Optional[str]:
        return self.bot_token or self.config.get('bot_token')

    def _api_get(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        bot_token = self._get_bot_token()
        if not bot_token:
            return None
        try:
            url = f"https://api.telegram.org/bot{bot_token}/{method}"
            resp = requests.get(url, params=params or {}, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get('ok'):
                return None
            return data
        except Exception:
            return None
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        bot_token = self._get_bot_token()
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
    
    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        import random
        self.verification_code = f"{random.randint(100000, 999999)}"
        return self.verification_code
    
    def send_verification_code(self, username: str) -> bool:
        """Send verification code to user (this requires manual user action)"""
        if not self.bot_token:
            return False
        
        try:
            # Generate code
            code = self.generate_verification_code()
            
            # Store code temporarily (in a real implementation, you'd store this in Redis/DB)
            # For now, we'll return it to user to display
            print(f"Verification code for @{username}: {code}")

            _telegram_pending_verifications[username.lower().lstrip('@')] = code
            
            return True
        except Exception as e:
            print(f"Failed to send verification code: {e}")
            return False
    
    def verify_chat_id(self, username: str, code: str) -> bool:
        """Verify code and extract chat_id from message"""
        uname = username.lower().lstrip('@')
        expected = _telegram_pending_verifications.get(uname)
        if not expected or expected != code:
            return False

        updates = self._api_get('getUpdates')
        if not updates:
            return False

        for upd in updates.get('result', []):
            msg = upd.get('message') or upd.get('edited_message')
            if not msg:
                continue
            from_user = msg.get('from') or {}
            from_username = (from_user.get('username') or '').lower()
            text = (msg.get('text') or '').strip()
            if from_username == uname and text == code:
                chat = msg.get('chat') or {}
                chat_id = chat.get('id')
                if chat_id is None:
                    continue
                self.verified_chat_id = str(chat_id)
                del _telegram_pending_verifications[uname]
                return True

        return False
    
    def send_alert(self, monitor_id: str, status: str, message: str, **kwargs) -> bool:
        if not self.enabled or not self.destination:
            return False
        
        try:
            bot_token = self._get_bot_token()
            if not bot_token:
                return False
            
            # Extract chat ID from webhook URL or use directly
            chat_id = self.destination
            if chat_id.startswith('@'):
                # In a real implementation, this would be the verified chat_id
                # For now, we'll use the username as a fallback
                pass
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Create message with emoji and formatting
            text = f"""
🚨 *Monitor Alert*

🔧 **Monitor:** {monitor_id}
📊 **Status:** {status}
📝 **Message:** {message}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print(f"Telegram notification sent successfully to {chat_id}")
                    return True
            
            print(f"Telegram notification failed: {response.text}")
            return False
            
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False


class NotificationManager:
    """Manages all notification services"""
    
    def __init__(self, db_manager=None):
        self.services = {
            'NTFY': NtfyService,
            'EMAIL': EmailService, 
            'TELEGRAM': TelegramService,
            'SLACK': SlackService
        }
        self.db = db_manager
    
    def create_service(self, notification_type: str, config: Dict[str, Any], bot_config: Dict[str, Any] = None) -> NotificationService:
        """Create notification service instance"""
        service_class = self.services.get(notification_type, NotificationService)
        
        # Merge bot_config into config for services that need additional parameters
        if bot_config:
            merged_config = {**config, **bot_config}
        else:
            merged_config = config
            
        return service_class(merged_config)
    
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
    
    def send_incident_alert(self, incident_id: str, trace_id: str, severity: str, rca: Dict, logs: list):
        """Send incident alert with RCA information to configured channels"""
        try:
            # Fetch enabled notification channels from database
            notifications = []
            if self.db:
                with self.db.postgres_conn.cursor() as cur:
                    cur.execute(
                        "SELECT type, config, enabled FROM notification_channels WHERE enabled = true"
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        notifications.append({
                            'type': row[0],
                            'config': json.loads(row[1]) if row[1] else {},
                            'enabled': row[2]
                        })
            
            if not notifications:
                print("No enabled notification channels found")
                return
            
            # Build incident message
            root_cause = rca.get('root_cause', 'Unknown')
            classification = rca.get('classification', 'Unknown')
            impact = rca.get('impact', '')
            
            message = f"""INCIDENT ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Incident ID: {incident_id}
Trace ID: {trace_id}
Severity: {severity}
Classification: {classification}

Root Cause:
{root_cause}

Impact:
{impact}

Claude agent has been triggered to investigate and create a fix.
"""
            
            # Send to all channels
            results = self.send_alerts(
                monitor_id=incident_id,
                notifications=notifications,
                status=severity,
                message=message
            )
            
            print(f"Incident alerts sent: {results}")
            return results
            
        except Exception as e:
            print(f"Failed to send incident alerts: {e}")
            return {}

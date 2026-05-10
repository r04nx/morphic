"""Email alert channel for Morphic"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class EmailChannel:
    """Email alert channel with SMTP support"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_email = config.get('from_email', '')
        self.to_email = config.get('to_email', '')
    
    def send(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email alert"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not all([self.username, self.password, self.from_email, self.to_email]):
            return {"success": False, "error": "Incomplete email configuration"}
        
        try:
            # Build email content
            subject = self._build_subject(alert_data)
            body = self._build_body(alert_data)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"[EmailChannel] Alert sent to {self.to_email}")
            return {"success": True, "channel": "email", "recipient": self.to_email}
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[EmailChannel] Authentication failed: {e}")
            return {"success": False, "error": "Authentication failed", "channel": "email"}
        except smtplib.SMTPException as e:
            logger.error(f"[EmailChannel] SMTP error: {e}")
            return {"success": False, "error": str(e), "channel": "email"}
        except Exception as e:
            logger.error(f"[EmailChannel] Failed to send: {e}")
            return {"success": False, "error": str(e), "channel": "email"}
    
    def _build_subject(self, alert_data: Dict[str, Any]) -> str:
        """Build email subject"""
        severity = alert_data.get('severity', 'INFO')
        trace_id = alert_data.get('trace_id', 'unknown')
        classification = alert_data.get('classification', 'Incident')
        return f"[Morphic] {severity} - {classification} (Trace: {trace_id[:8]})"
    
    def _build_body(self, alert_data: Dict[str, Any]) -> str:
        """Build HTML email body"""
        severity = alert_data.get('severity', 'INFO')
        trace_id = alert_data.get('trace_id', 'unknown')
        classification = alert_data.get('classification', 'Unknown')
        root_cause = alert_data.get('root_cause', 'Analyzing...')
        impact = alert_data.get('impact', 'No impact assessment available')
        confidence = alert_data.get('confidence_score', 0.0)
        
        color = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#ca8a04',
            'LOW': '#16a34a',
            'INFO': '#2563eb'
        }.get(severity, '#2563eb')
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #f3f4f6;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="background: {color}; color: white; padding: 20px;">
                    <h2 style="margin: 0;">Morphic Alert - {severity}</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Trace ID: {trace_id}</p>
                </div>
                <div style="padding: 20px;">
                    <h3 style="color: #111827; margin-top: 0;">{classification}</h3>
                    
                    <div style="background: #f9fafb; padding: 15px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #374151;"><strong>Root Cause:</strong> {root_cause}</p>
                    </div>
                    
                    <div style="background: #f9fafb; padding: 15px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #374151;"><strong>Impact:</strong> {impact}</p>
                    </div>
                    
                    <p style="color: #6b7280; font-size: 14px;">
                        Confidence Score: {confidence:.0%}<br>
                        Timestamp: {alert_data.get('timestamp', 'N/A')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test(self) -> Dict[str, Any]:
        """Test email configuration"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not all([self.username, self.password, self.from_email, self.to_email]):
            return {"success": False, "error": "Incomplete configuration"}
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(self.username, self.password)
                return {"success": True, "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "error": str(e)}

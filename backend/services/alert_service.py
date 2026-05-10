"""Centralized alert service for Morphic"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.settings import Config
from services.channels.email_channel import EmailChannel
from services.channels.slack_channel import SlackChannel
from services.channels.webhook_channel import WebhookChannel


logger = logging.getLogger(__name__)


class AlertService:
    """Centralized service for dispatching alerts across multiple channels"""
    
    def __init__(self):
        self.channels = {}
        self._initialize_channels()
    
    def _initialize_channels(self):
        """Initialize enabled alert channels from config"""
        # Email channel
        email_config = {
            'enabled': bool(Config.EMAIL_USER and Config.EMAIL_PASSWORD),
            'smtp_host': getattr(Config, 'SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': getattr(Config, 'SMTP_PORT', 587),
            'username': getattr(Config, 'EMAIL_USER', ''),
            'password': getattr(Config, 'EMAIL_PASSWORD', ''),
            'from_email': getattr(Config, 'EMAIL_FROM', Config.EMAIL_USER if hasattr(Config, 'EMAIL_USER') else ''),
            'to_email': getattr(Config, 'ALERT_EMAIL', Config.EMAIL_USER if hasattr(Config, 'EMAIL_USER') else '')
        }
        self.channels['email'] = EmailChannel(email_config)
        
        # Slack channel
        slack_config = {
            'enabled': hasattr(Config, 'SLACK_WEBHOOK_URL') and bool(Config.SLACK_WEBHOOK_URL),
            'webhook_url': getattr(Config, 'SLACK_WEBHOOK_URL', ''),
            'timeout': 10
        }
        self.channels['slack'] = SlackChannel(slack_config)
        
        # Generic webhook channel
        webhook_config = {
            'enabled': hasattr(Config, 'WEBHOOK_URL') and bool(Config.WEBHOOK_URL),
            'webhook_url': getattr(Config, 'WEBHOOK_URL', ''),
            'timeout': 10,
            'headers': getattr(Config, 'WEBHOOK_HEADERS', {})
        }
        self.channels['webhook'] = WebhookChannel(webhook_config)
        
        enabled_count = sum(1 for ch in self.channels.values() if ch.enabled)
        logger.info(f"[AlertService] Initialized {enabled_count} channel(s)")
    
    def send_alert(self, alert_data: Dict[str, Any], channels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send alert to specified channels or all enabled channels
        
        Args:
            alert_data: Alert payload with severity, trace_id, classification, etc.
            channels: List of channel names to use (None = all enabled)
        
        Returns:
            Dict with results per channel
        """
        # Add timestamp if not present
        if 'timestamp' not in alert_data:
            alert_data['timestamp'] = datetime.utcnow().isoformat()
        
        results = {
            'success': False,
            'channels': {},
            'sent_count': 0,
            'failed_count': 0,
            'timestamp': alert_data['timestamp']
        }
        
        # Determine which channels to use
        target_channels = channels or list(self.channels.keys())
        
        # Send to each channel
        for channel_name in target_channels:
            if channel_name not in self.channels:
                results['channels'][channel_name] = {
                    'success': False,
                    'error': 'Channel not configured'
                }
                results['failed_count'] += 1
                continue
            
            channel = self.channels[channel_name]
            try:
                channel_result = channel.send(alert_data)
                results['channels'][channel_name] = channel_result
                
                if channel_result.get('success'):
                    results['sent_count'] += 1
                else:
                    results['failed_count'] += 1
                    
            except Exception as e:
                logger.error(f"[AlertService] Channel {channel_name} failed: {e}")
                results['channels'][channel_name] = {
                    'success': False,
                    'error': str(e)
                }
                results['failed_count'] += 1
        
        # Overall success if at least one channel succeeded
        results['success'] = results['sent_count'] > 0
        
        logger.info(f"[AlertService] Alert dispatched: {results['sent_count']} sent, {results['failed_count']} failed")
        return results
    
    def test_channels(self, channels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Test configured channels"""
        target_channels = channels or list(self.channels.keys())
        results = {}
        
        for channel_name in target_channels:
            if channel_name in self.channels:
                results[channel_name] = self.channels[channel_name].test()
            else:
                results[channel_name] = {'success': False, 'error': 'Channel not found'}
        
        return results
    
    def get_channel_status(self) -> Dict[str, Any]:
        """Get status of all channels"""
        return {
            name: {
                'enabled': ch.enabled,
                'configured': self._is_channel_configured(name)
            }
            for name, ch in self.channels.items()
        }
    
    def _is_channel_configured(self, channel_name: str) -> bool:
        """Check if a channel has minimum required configuration"""
        ch = self.channels.get(channel_name)
        if not ch:
            return False
        
        if channel_name == 'email':
            return bool(ch.username and ch.password and ch.to_email)
        elif channel_name == 'slack':
            return bool(ch.webhook_url)
        elif channel_name == 'webhook':
            return bool(ch.webhook_url)
        
        return False

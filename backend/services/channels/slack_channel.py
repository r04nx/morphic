"""Slack webhook alert channel for Morphic"""
import requests
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__)


class SlackChannel:
    """Slack webhook alert channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.webhook_url = config.get('webhook_url', '')
        self.timeout = config.get('timeout', 10)
    
    def send(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack alert via webhook"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not self.webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            payload = self._build_payload(alert_data)
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("[SlackChannel] Alert sent successfully")
                return {"success": True, "channel": "slack"}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"[SlackChannel] {error_msg}")
                return {"success": False, "error": error_msg, "channel": "slack"}
                
        except requests.exceptions.Timeout:
            logger.error("[SlackChannel] Request timed out")
            return {"success": False, "error": "Request timeout", "channel": "slack"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[SlackChannel] Request failed: {e}")
            return {"success": False, "error": str(e), "channel": "slack"}
        except Exception as e:
            logger.error(f"[SlackChannel] Unexpected error: {e}")
            return {"success": False, "error": str(e), "channel": "slack"}
    
    def _build_payload(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Slack webhook payload"""
        severity = alert_data.get('severity', 'INFO')
        trace_id = alert_data.get('trace_id', 'unknown')
        classification = alert_data.get('classification', 'Unknown')
        root_cause = alert_data.get('root_cause', 'Analyzing...')
        impact = alert_data.get('impact', 'No impact assessment')
        confidence = alert_data.get('confidence_score', 0.0)
        
        # Color based on severity
        color_map = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#ca8a04',
            'LOW': '#16a34a',
            'INFO': '#2563eb'
        }
        color = color_map.get(severity, '#2563eb')
        
        return {
            "attachments": [
                {
                    "color": color,
                    "title": f"Morphic Alert - {severity}",
                    "title_link": f"http://localhost:3000/incidents?trace={trace_id}",
                    "fields": [
                        {
                            "title": "Classification",
                            "value": classification,
                            "short": True
                        },
                        {
                            "title": "Trace ID",
                            "value": trace_id[:8],
                            "short": True
                        },
                        {
                            "title": "Root Cause",
                            "value": root_cause[:100] + ('...' if len(root_cause) > 100 else ''),
                            "short": False
                        },
                        {
                            "title": "Impact",
                            "value": impact[:100] + ('...' if len(impact) > 100 else ''),
                            "short": False
                        },
                        {
                            "title": "Confidence",
                            "value": f"{confidence:.0%}",
                            "short": True
                        }
                    ],
                    "footer": "Morphic AI",
                    "ts": alert_data.get('timestamp', '')
                }
            ]
        }
    
    def test(self) -> Dict[str, Any]:
        """Test Slack webhook"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not self.webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            test_payload = {"text": "Morphic test message - Slack integration is working!"}
            response = requests.post(
                self.webhook_url,
                json=test_payload,
                timeout=5
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Webhook test successful"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

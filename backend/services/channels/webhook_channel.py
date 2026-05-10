"""Generic webhook alert channel for Morphic"""
import requests
import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class WebhookChannel:
    """Generic webhook alert channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.webhook_url = config.get('webhook_url', '')
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 10)
        self.method = config.get('method', 'POST')
    
    def send(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook alert"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not self.webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            payload = self._build_payload(alert_data)
            headers = {
                'Content-Type': 'application/json',
                **self.headers
            }
            
            response = requests.request(
                method=self.method,
                url=self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"[WebhookChannel] Alert sent to {self.webhook_url}")
                return {"success": True, "channel": "webhook", "status_code": response.status_code}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"[WebhookChannel] {error_msg}")
                return {"success": False, "error": error_msg, "channel": "webhook"}
                
        except requests.exceptions.Timeout:
            logger.error("[WebhookChannel] Request timed out")
            return {"success": False, "error": "Request timeout", "channel": "webhook"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[WebhookChannel] Request failed: {e}")
            return {"success": False, "error": str(e), "channel": "webhook"}
        except Exception as e:
            logger.error(f"[WebhookChannel] Unexpected error: {e}")
            return {"success": False, "error": str(e), "channel": "webhook"}
    
    def _build_payload(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build generic webhook payload"""
        return {
            "source": "morphic",
            "version": "2.0.0",
            "alert": {
                "severity": alert_data.get('severity', 'INFO'),
                "trace_id": alert_data.get('trace_id'),
                "classification": alert_data.get('classification'),
                "root_cause": alert_data.get('root_cause'),
                "impact": alert_data.get('impact'),
                "confidence_score": alert_data.get('confidence_score'),
                "timestamp": alert_data.get('timestamp'),
                "blast_radius": alert_data.get('blast_radius'),
                "suggested_fix": alert_data.get('suggested_fix'),
                "incident_id": alert_data.get('incident_id')
            },
            "metadata": {
                "service": alert_data.get('service', 'morphic-ai'),
                "environment": alert_data.get('environment', 'production')
            }
        }
    
    def test(self) -> Dict[str, Any]:
        """Test webhook"""
        if not self.enabled:
            return {"success": False, "error": "Channel disabled"}
        
        if not self.webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            test_payload = {
                "source": "morphic",
                "version": "2.0.0",
                "test": True,
                "message": "Morphic webhook test"
            }
            
            response = requests.request(
                method=self.method,
                url=self.webhook_url,
                json=test_payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code in [200, 201, 202, 204]:
                return {"success": True, "message": f"Webhook test successful (HTTP {response.status_code})"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

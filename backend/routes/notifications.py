"""Notification routes for Morphic backend"""
from flask import jsonify, request
from services.notifications import NotificationManager


def register_notification_routes(app, monitor_manager):
    """Register notification routes"""
    notification_manager = NotificationManager()
    
    @app.route('/api/notifications/test', methods=['POST'])
    def test_notification():
        """Test notification configuration"""
        try:
            data = request.get_json()
            notification_type = data.get('type')
            config = data.get('config', {})
            bot_config = data.get('bot_config', {})
            monitor_id = data.get('monitor_id', 'test-monitor')
            
            if not notification_type:
                return jsonify({"error": "Notification type is required"}), 400
            
            service = notification_manager.create_service(notification_type, config, bot_config)
            
            # First test connection (but allow email to proceed even if test fails)
            if hasattr(service, 'test_connection'):
                connection_success = service.test_connection()
                if not connection_success and notification_type != 'EMAIL':
                    return jsonify({
                        "success": False,
                        "message": "Connection test failed - please check your configuration"
                    })
                # For EmailService, always try to send the test email regardless of connection test
                if notification_type == 'EMAIL':
                    print("Email connection test result:", connection_success, "- proceeding with test send anyway")
            
            # Then send test notification
            success = service.send_alert(
                monitor_id=monitor_id,
                status="DEGRADED", 
                message="This is a test notification from Morphic"
            )
            
            return jsonify({
                "success": success,
                "message": "Test notification sent successfully" if success else "Test notification failed"
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/notifications/send', methods=['POST'])
    def send_notification():
        """Send notification to configured channels"""
        try:
            data = request.get_json()
            monitor_id = data.get('monitor_id')
            status = data.get('status')
            message = data.get('message', 'Status change detected')
            
            if not monitor_id or not status:
                return jsonify({"error": "monitor_id and status are required"}), 400
            
            # Get monitor with notifications
            monitor = monitor_manager.get_monitor(monitor_id)
            if not monitor:
                return jsonify({"error": "Monitor not found"}), 404
            
            notifications = monitor.get('notifications', [])
            
            # Send alerts to all configured channels
            results = notification_manager.send_alerts(
                monitor_id=monitor_id,
                notifications=notifications,
                status=status,
                message=message
            )
            
            return jsonify({
                "success": True,
                "results": results,
                "sent_count": sum(1 for success in results.values() if success),
                "total_count": len(results)
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

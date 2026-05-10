"""Notification routes for Morphic backend"""
from flask import jsonify, request
from services.notifications import NotificationManager
import os


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
    
    @app.route('/api/notifications/telegram/send-code', methods=['POST'])
    def send_telegram_verification_code():
        """Send verification code to Telegram user"""
        try:
            data = request.get_json()
            username = data.get('username')
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            bot_username = os.getenv('TELEGRAM_BOT_USERNAME', '').lstrip('@')
            
            if not username:
                return jsonify({"error": "username is required"}), 400

            if not bot_token or not bot_username:
                return jsonify({"error": "Telegram bot is not configured"}), 500
            
            # Create Telegram service instance
            config = {'destination': username}
            service = notification_manager.create_service('TELEGRAM', config)
            
            # Generate and send verification code
            code = service.generate_verification_code()
            success = service.send_verification_code(username)
            
            if success:
                return jsonify({
                    "success": True,
                    "bot_username": bot_username,
                    "verification_code": code,
                    "message": f"Send this code to your Telegram bot: {code}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to send verification code"
                }), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/notifications/telegram/verify', methods=['POST'])
    def verify_telegram_chat_id():
        """Verify Telegram chat ID with code"""
        try:
            data = request.get_json()
            print(f"[DEBUG] Telegram verify request data: {data}")
            username = data.get('username')
            code = data.get('code')
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            print(f"[DEBUG] Parsed - username: {username}, code: {code}")

            if not username or not code:
                print(f"[DEBUG] Missing required fields - username: {username}, code: {code}")
                return jsonify({"error": "username and code are required"}), 400

            if not bot_token:
                return jsonify({"error": "Telegram bot is not configured"}), 500
            
            # Create Telegram service instance
            config = {'destination': username}
            service = notification_manager.create_service('TELEGRAM', config)
            
            # Verify the code
            success = service.verify_chat_id(username, code)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Telegram verification successful",
                    "chat_id": service.verified_chat_id
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid verification code"
                }), 400
                
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

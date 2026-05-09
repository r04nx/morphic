"""Settings routes for Morphic backend"""
from flask import jsonify, request


def register_settings_routes(app, settings_manager):
    """Register settings routes"""
    
    @app.route('/api/settings', methods=['GET', 'POST', 'PUT'])
    def settings():
        """Handle global settings"""
        if request.method == 'GET':
            try:
                settings = settings_manager.get_all_settings()
                return jsonify({
                    "success": True,
                    "settings": settings
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method in ['POST', 'PUT']:
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                results = {}
                for key, value in data.items():
                    success = settings_manager.set_setting(key, value)
                    results[key] = success
                
                return jsonify({
                    "success": True,
                    "results": results
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    @app.route('/api/settings/<key>', methods=['GET', 'PUT', 'DELETE', 'POST'])
    def setting_detail(key):
        """Handle specific setting"""
        if request.method == 'GET':
            try:
                value = settings_manager.get_setting(key)
                if value is not None:
                    return jsonify({
                        "success": True,
                        "key": key,
                        "value": value
                    })
                else:
                    return jsonify({"error": "Setting not found"}), 404
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'POST' and key == 'smtp':
            """Test SMTP connection"""
            try:
                from services.notifications import EmailService
                
                email_service = EmailService({}, settings_manager)
                success = email_service.test_connection()
                
                return jsonify({
                    "success": success,
                    "message": "SMTP connection successful" if success else "SMTP connection failed - check credentials"
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                if 'value' not in data:
                    return jsonify({"error": "Value is required"}), 400
                
                success = settings_manager.set_setting(key, data['value'])
                if success:
                    return jsonify({
                        "success": True,
                        "key": key,
                        "value": data['value']
                    })
                else:
                    return jsonify({"error": "Failed to save setting"}), 500
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        elif request.method == 'DELETE':
            try:
                success = settings_manager.delete_setting(key)
                if success:
                    return jsonify({
                        "success": True,
                        "message": f"Setting {key} deleted"
                    })
                else:
                    return jsonify({"error": "Setting not found"}), 404
            except Exception as e:
                return jsonify({"error": str(e)}), 500

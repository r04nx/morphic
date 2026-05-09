"""Log analysis service for Morphic backend"""
from datetime import datetime


class LogAIAnalyzer:
    """LogAI-based log analysis"""
    
    def __init__(self):
        self.logai_available = False
        try:
            import logai
            self.logai_available = True
            print("✅ LogAI available for analysis")
        except ImportError:
            print("⚠️ LogAI not available, using basic analysis")
    
    def analyze_logs(self, logs):
        """Analyze logs using LogAI or basic methods"""
        if not logs:
            return {"error": "No logs to analyze"}
        
        analysis = {
            "total_logs": len(logs),
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": {}
        }
        
        # Basic analysis
        levels = {}
        services = {}
        error_patterns = []
        
        for log in logs:
            # Count log levels
            level = log.get('level', 'INFO')
            levels[level] = levels.get(level, 0) + 1
            
            # Count services
            service = log.get('service', 'unknown')
            services[service] = services.get(service, 0) + 1
            
            # Look for error patterns
            message = str(log.get('message', '')).lower()
            if any(keyword in message for keyword in ['error', 'exception', 'failed', 'timeout']):
                error_patterns.append({
                    'timestamp': log.get('timestamp'),
                    'service': service,
                    'level': level,
                    'message': log.get('message')[:200] + '...' if len(str(log.get('message', ''))) > 200 else log.get('message')
                })
        
        analysis["analysis"]["log_levels"] = levels
        analysis["analysis"]["services"] = services
        analysis["analysis"]["error_patterns"] = error_patterns
        analysis["analysis"]["error_rate"] = (levels.get('ERROR', 0) + levels.get('CRITICAL', 0)) / len(logs) * 100
        
        # Calculate recommendations
        recommendations = []
        if analysis["analysis"]["error_rate"] > 5:
            recommendations.append("High error rate detected - immediate attention required")
        elif analysis["analysis"]["error_rate"] > 2:
            recommendations.append("Elevated error rate - monitor closely")
        
        if error_patterns:
            recommendations.append(f"Found {len(error_patterns)} error patterns - investigate root causes")
        
        analysis["recommendations"] = recommendations
        
        return analysis

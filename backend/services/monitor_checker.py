"""Background monitor checker service for Morphic backend"""
import threading
import time
import requests
from datetime import datetime


class MonitorChecker:
    """Background thread to check monitor URLs and update status"""
    
    def __init__(self, monitor_manager, interval_seconds=30):
        self.monitor_manager = monitor_manager
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
    
    def check_url(self, url, timeout=5):
        """Check a URL and return status and latency"""
        try:
            start_time = datetime.utcnow()
            response = requests.get(url, timeout=timeout)
            end_time = datetime.utcnow()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if response.status_code < 400:
                return 'UP', latency_ms
            else:
                return 'DOWN', latency_ms
        except Exception as e:
            return 'DOWN', 0
    
    def calculate_uptime(self, monitor_id):
        """Calculate uptime percentage from history"""
        try:
            history = self.monitor_manager.get_history(monitor_id, limit=100)
            if not history:
                return 100.0
            
            up_count = sum(1 for h in history if h['status'] == 'UP')
            return round((up_count / len(history)) * 100, 2)
        except:
            return 100.0
    
    def check_all_monitors(self):
        """Check all monitors and update their status"""
        try:
            monitors = self.monitor_manager.list_monitors()
            for monitor in monitors:
                monitor_id = monitor['id']
                url = monitor.get('url')
                
                if not url:
                    continue
                
                status, latency_ms = self.check_url(url)
                uptime_pct = self.calculate_uptime(monitor_id)
                
                # Update monitor in database
                self.monitor_manager.update_monitor(monitor_id, {
                    'status': status,
                    'latency_ms': latency_ms,
                    'uptime_pct': uptime_pct
                })
        except Exception as e:
            print(f"Monitor check error: {e}")
    
    def run(self):
        """Run the monitoring loop"""
        while self.running:
            self.check_all_monitors()
            time.sleep(self.interval_seconds)
    
    def start(self):
        """Start the monitoring thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("✅ Monitor checker started")
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join()
            print("⏹️ Monitor checker stopped")

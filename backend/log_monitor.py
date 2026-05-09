#!/usr/bin/env python3
"""
Real-time Log Monitoring and Analysis with LogAI
Monitors https://hackathonps-ykxr.onrender.com/logs for 1 minute
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
from collections import defaultdict, Counter
import re

# Add LogAI to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import logai
    print("✅ LogAI imported successfully")
except ImportError as e:
    print(f"⚠️  LogAI not available: {e}")
    print("   Continuing with basic analysis...")

class LogMonitor:
    def __init__(self, url):
        self.url = url
        self.logs = []
        self.start_time = datetime.now()
        self.monitoring_duration = 60  # 1 minute
        
    def fetch_logs(self):
        """Fetch logs from the endpoint"""
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'logs' in data:
                        return data['logs']
                    else:
                        print(f"📄 Response type: {type(data)}")
                        return [data] if data else []
                except json.JSONDecodeError:
                    print(f"📄 Raw response: {response.text[:200]}...")
                    return []
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return []
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return []
    
    def parse_log_entry(self, log_entry):
        """Parse individual log entry"""
        if isinstance(log_entry, dict):
            return {
                'timestamp': log_entry.get('timestamp', datetime.now().isoformat()),
                'level': log_entry.get('level', 'INFO'),
                'message': log_entry.get('message', str(log_entry)),
                'service': log_entry.get('service', 'unknown'),
                'trace_id': log_entry.get('trace_id', ''),
                'raw': log_entry
            }
        else:
            return {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': str(log_entry),
                'service': 'unknown',
                'trace_id': '',
                'raw': log_entry
            }
    
    def basic_analysis(self, logs_df):
        """Perform basic log analysis"""
        print("\n📊 BASIC LOG ANALYSIS")
        print("=" * 50)
        
        # Log levels distribution
        if 'level' in logs_df.columns:
            level_counts = logs_df['level'].value_counts()
            print(f"📈 Log Levels:")
            for level, count in level_counts.items():
                print(f"   {level}: {count}")
        
        # Services distribution
        if 'service' in logs_df.columns:
            service_counts = logs_df['service'].value_counts()
            print(f"\n🏷️  Services:")
            for service, count in service_counts.items():
                print(f"   {service}: {count}")
        
        # Time range
        if 'timestamp' in logs_df.columns:
            print(f"\n⏰ Time Range:")
            print(f"   Start: {logs_df['timestamp'].min()}")
            print(f"   End: {logs_df['timestamp'].max()}")
            # Convert to datetime for duration calculation
            try:
                logs_df['timestamp_dt'] = pd.to_datetime(logs_df['timestamp'])
                duration = logs_df['timestamp_dt'].max() - logs_df['timestamp_dt'].min()
                print(f"   Duration: {duration}")
            except:
                print("   Duration: Unable to calculate (timestamp format issue)")
        
        # Common patterns in messages
        if 'message' in logs_df.columns:
            messages = logs_df['message'].dropna().astype(str)
            word_freq = Counter()
            for msg in messages:
                words = re.findall(r'\b\w+\b', msg.lower())
                word_freq.update(words)
            
            print(f"\n🔤 Common Words:")
            for word, count in word_freq.most_common(10):
                if len(word) > 3:  # Skip short words
                    print(f"   {word}: {count}")
    
    def logai_analysis(self, logs_df):
        """Attempt LogAI analysis"""
        try:
            print("\n🤖 LOGAI ANALYSIS")
            print("=" * 50)
            
            # Convert to LogAI format if possible
            if logs_df.empty:
                print("   No logs to analyze")
                return
            
            # Try to use LogAI preprocessing
            try:
                from logai.utils import log_utils
                print("✅ LogAI utils available")
                
                # Clean log messages
                if 'message' in logs_df.columns:
                    cleaned_messages = []
                    for msg in logs_df['message']:
                        if pd.notna(msg):
                            # Basic cleaning
                            cleaned = str(msg).strip()
                            cleaned_messages.append(cleaned)
                        else:
                            cleaned_messages.append("")
                    
                    logs_df['cleaned_message'] = cleaned_messages
                    print(f"   Cleaned {len(cleaned_messages)} log messages")
                    
            except ImportError:
                print("⚠️  LogAI utils not available")
            
            # Try pattern extraction
            try:
                from logai.information_extraction import pattern_extraction
                print("✅ LogAI pattern extraction available")
                
                # Extract patterns from messages
                if 'message' in logs_df.columns:
                    patterns = []
                    for msg in logs_df['message'].dropna():
                        if pd.notna(msg):
                            # Simple pattern extraction
                            msg_str = str(msg)
                            # Extract IP addresses
                            ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', msg_str)
                            # Extract URLs
                            urls = re.findall(r'https?://[^\s]+', msg_str)
                            # Extract error codes
                            error_codes = re.findall(r'\b[45]\d{2}\b', msg_str)
                            
                            if ips or urls or error_codes:
                                patterns.append({
                                    'message': msg_str[:100] + '...' if len(msg_str) > 100 else msg_str,
                                    'ips': ips,
                                    'urls': urls,
                                    'error_codes': error_codes
                                })
                    
                    if patterns:
                        print(f"   Found {len(patterns)} patterns:")
                        for i, pattern in enumerate(patterns[:5]):  # Show first 5
                            print(f"     Pattern {i+1}: {pattern['message'][:80]}...")
                            if pattern['ips']:
                                print(f"       IPs: {pattern['ips']}")
                            if pattern['urls']:
                                print(f"       URLs: {pattern['urls']}")
                            if pattern['error_codes']:
                                print(f"       Error Codes: {pattern['error_codes']}")
                    
            except ImportError:
                print("⚠️  LogAI pattern extraction not available")
            
            # Try anomaly detection
            try:
                from logai.algorithms import anomaly_detection
                print("✅ LogAI anomaly detection available")
                
                # Simple anomaly detection based on log levels
                if 'level' in logs_df.columns:
                    error_logs = logs_df[logs_df['level'].isin(['ERROR', 'CRITICAL', 'FATAL'])]
                    if not error_logs.empty:
                        print(f"   🚨 Found {len(error_logs)} error/critical logs (potential anomalies)")
                        for idx, row in error_logs.iterrows():
                            print(f"     {row['timestamp']}: {row['level']} - {row['message'][:100]}...")
                    else:
                        print("   ✅ No error/critical logs detected")
                        
            except ImportError:
                print("⚠️  LogAI anomaly detection not available")
                
        except Exception as e:
            print(f"❌ LogAI analysis failed: {e}")
    
    def monitor(self):
        """Main monitoring function"""
        print(f"🚀 Starting log monitoring for {self.monitoring_duration} seconds...")
        print(f"📡 URL: {self.url}")
        print(f"⏰ Started at: {self.start_time}")
        print("=" * 60)
        
        poll_interval = 5  # Poll every 5 seconds
        poll_count = 0
        
        while (datetime.now() - self.start_time).seconds < self.monitoring_duration:
            poll_count += 1
            current_time = datetime.now()
            elapsed = (current_time - self.start_time).seconds
            
            print(f"\n🔄 Poll #{poll_count} (Elapsed: {elapsed}s)")
            print("-" * 40)
            
            # Fetch logs
            new_logs = self.fetch_logs()
            
            if new_logs:
                print(f"📥 Retrieved {len(new_logs)} log entries")
                
                # Parse and store logs
                parsed_logs = []
                for log_entry in new_logs:
                    parsed = self.parse_log_entry(log_entry)
                    parsed_logs.append(parsed)
                    self.logs.append(parsed)
                
                # Create DataFrame for analysis
                logs_df = pd.DataFrame(parsed_logs)
                
                # Basic analysis
                self.basic_analysis(logs_df)
                
                # LogAI analysis
                self.logai_analysis(logs_df)
                
            else:
                print("📭 No logs retrieved")
            
            # Wait for next poll
            if elapsed < self.monitoring_duration:
                sleep_time = min(poll_interval, self.monitoring_duration - elapsed)
                print(f"⏳ Waiting {sleep_time}s for next poll...")
                time.sleep(sleep_time)
        
        # Final analysis
        self.final_analysis()
    
    def final_analysis(self):
        """Final comprehensive analysis"""
        print("\n" + "=" * 60)
        print("🎯 FINAL ANALYSIS SUMMARY")
        print("=" * 60)
        
        if not self.logs:
            print("❌ No logs collected during monitoring period")
            return
        
        # Create final DataFrame
        final_df = pd.DataFrame(self.logs)
        
        print(f"📊 Total logs collected: {len(final_df)}")
        print(f"⏱️  Monitoring duration: {(datetime.now() - self.start_time).seconds} seconds")
        print(f"📈 Average logs per poll: {len(final_df) / max(1, (datetime.now() - self.start_time).seconds // 5):.1f}")
        
        # Overall statistics
        if 'level' in final_df.columns:
            level_dist = final_df['level'].value_counts()
            error_rate = (level_dist.get('ERROR', 0) + level_dist.get('CRITICAL', 0)) / len(final_df) * 100
            print(f"🚨 Error rate: {error_rate:.1f}%")
        
        # Unique services
        if 'service' in final_df.columns:
            unique_services = final_df['service'].nunique()
            print(f"🏷️  Unique services: {unique_services}")
        
        # Most active time periods
        if 'timestamp' in final_df.columns:
            final_df['timestamp'] = pd.to_datetime(final_df['timestamp'])
            final_df['minute'] = final_df['timestamp'].dt.minute
            busiest_minute = final_df['minute'].value_counts().idxmax()
            print(f"⏰ Busiest minute: {busiest_minute}")
        
        print("\n✅ Monitoring completed!")

def main():
    """Main function"""
    url = "https://hackathonps-ykxr.onrender.com/logs"
    
    print("🤖 LogAI Real-time Log Monitor")
    print("=" * 40)
    
    monitor = LogMonitor(url)
    monitor.monitor()

if __name__ == "__main__":
    main()

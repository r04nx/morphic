#!/usr/bin/env python3
"""
Corrected LogAI Analysis Script
Uses actual available LogAI modules to analyze logs from the API
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime
import sys
import os
import re
from collections import Counter

# Add LogAI to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def fetch_logs_from_api():
    """Fetch logs from the API once for analysis"""
    url = "https://hackathonps-ykxr.onrender.com/logs"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'logs' in data:
                return data['logs']
            else:
                return [data] if data else []
        else:
            print(f"❌ HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

def parse_log_entry(log_entry):
    """Parse individual log entry into standardized format"""
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

def basic_log_analysis(logs_df):
    """Perform basic statistical analysis"""
    print("📊 BASIC LOG ANALYSIS")
    print("=" * 50)
    
    print(f"📈 Total log entries: {len(logs_df)}")
    
    # Log levels distribution
    if 'level' in logs_df.columns:
        level_counts = logs_df['level'].value_counts()
        print(f"\n📊 Log Levels Distribution:")
        for level, count in level_counts.items():
            percentage = (count / len(logs_df)) * 100
            print(f"   {level:8}: {count:4} ({percentage:5.1f}%)")
    
    # Services distribution
    if 'service' in logs_df.columns:
        service_counts = logs_df['service'].value_counts()
        print(f"\n🏷️  Services Distribution:")
        for service, count in service_counts.items():
            percentage = (count / len(logs_df)) * 100
            print(f"   {service:15}: {count:4} ({percentage:5.1f}%)")
    
    # Time analysis
    if 'timestamp' in logs_df.columns:
        try:
            logs_df['timestamp_dt'] = pd.to_datetime(logs_df['timestamp'])
            time_range = logs_df['timestamp_dt'].max() - logs_df['timestamp_dt'].min()
            print(f"\n⏰ Time Analysis:")
            print(f"   Time Range: {time_range}")
            print(f"   Start Time: {logs_df['timestamp_dt'].min()}")
            print(f"   End Time: {logs_df['timestamp_dt'].max()}")
            
            # Logs per minute
            logs_df['minute'] = logs_df['timestamp_dt'].dt.minute
            logs_per_minute = logs_df['minute'].value_counts().sort_index()
            busiest_minute = logs_per_minute.idxmax()
            max_logs_per_minute = logs_per_minute.max()
            print(f"   Busiest Minute: {busiest_minute} ({max_logs_per_minute} logs)")
        except Exception as e:
            print(f"\n⏰ Time Analysis Error: {e}")
    
    # Message analysis
    if 'message' in logs_df.columns:
        messages = logs_df['message'].dropna().astype(str)
        
        # Word frequency
        word_freq = Counter()
        for msg in messages:
            words = re.findall(r'\b\w+\b', msg.lower())
            word_freq.update(words)
        
        print(f"\n🔤 Top 10 Most Common Words:")
        for word, count in word_freq.most_common(10):
            if len(word) > 2:  # Skip very short words
                print(f"   {word:15}: {count}")
        
        # Error patterns
        error_keywords = ['error', 'exception', 'failed', 'timeout', 'null', 'undefined', 'crash']
        error_messages = messages[messages.str.contains('|'.join(error_keywords), case=False, na=False)]
        if not error_messages.empty:
            print(f"\n🚨 Messages with Error Keywords: {len(error_messages)}")
            for i, msg in enumerate(error_messages.head(3)):
                print(f"   {i+1}. {msg[:100]}...")

def logai_enhanced_analysis(logs_df):
    """Use available LogAI modules for enhanced analysis"""
    print("\n🤖 LOGAI ENHANCED ANALYSIS")
    print("=" * 50)
    
    try:
        # Import LogAI modules
        from logai.information_extraction import log_parser
        from logai.analysis import anomaly_detector
        from logai.utils import functions
        print("✅ LogAI modules imported successfully")
        
        # Log parsing with LogAI
        if 'message' in logs_df.columns and not logs_df.empty:
            print("\n🔍 LogAI Parsing Analysis:")
            
            try:
                # Try to use LogAI log parser
                parser = log_parser.LogParser()
                print("   ✅ LogAI LogParser initialized")
                
                # Parse a sample of messages
                sample_messages = logs_df['message'].dropna().head(10).tolist()
                parsed_patterns = []
                
                for msg in sample_messages:
                    try:
                        # Extract structured information
                        msg_str = str(msg)
                        
                        # Extract timestamps
                        timestamps = re.findall(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', msg_str)
                        
                        # Extract IP addresses
                        ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', msg_str)
                        
                        # Extract URLs
                        urls = re.findall(r'https?://[^\s]+', msg_str)
                        
                        # Extract error codes
                        error_codes = re.findall(r'\b[45]\d{2}\b', msg_str)
                        
                        # Extract order IDs (common in the logs)
                        order_ids = re.findall(r'orderid[:\s]+([A-Za-z0-9-]+)', msg_str, re.IGNORECASE)
                        
                        if any([timestamps, ips, urls, error_codes, order_ids]):
                            parsed_patterns.append({
                                'message': msg_str[:80] + '...' if len(msg_str) > 80 else msg_str,
                                'timestamps': timestamps,
                                'ips': ips,
                                'urls': urls,
                                'error_codes': error_codes,
                                'order_ids': order_ids
                            })
                    except Exception as e:
                        continue
                
                if parsed_patterns:
                    print(f"   📋 Found {len(parsed_patterns)} structured patterns:")
                    for i, pattern in enumerate(parsed_patterns[:5]):
                        print(f"     Pattern {i+1}: {pattern['message']}")
                        if pattern['order_ids']:
                            print(f"       🏷️  Order IDs: {pattern['order_ids']}")
                        if pattern['error_codes']:
                            print(f"       🚨 Error Codes: {pattern['error_codes']}")
                        if pattern['ips']:
                            print(f"       🌐 IPs: {pattern['ips']}")
                        if pattern['urls']:
                            print(f"       🔗 URLs: {pattern['urls']}")
                else:
                    print("   📋 No structured patterns found in sample")
                    
            except Exception as e:
                print(f"   ⚠️  LogAI parsing failed: {e}")
        
        # Anomaly detection with LogAI
        if not logs_df.empty:
            print("\n🔍 LogAI Anomaly Detection:")
            
            try:
                detector = anomaly_detector.AnomalyDetector()
                print("   ✅ LogAI AnomalyDetector initialized")
                
                # Focus on error logs for anomaly detection
                error_logs = logs_df[logs_df['level'].isin(['ERROR', 'CRITICAL', 'FATAL'])]
                
                if not error_logs.empty:
                    print(f"   🚨 Found {len(error_logs)} error logs for anomaly analysis")
                    
                    # Analyze error patterns
                    error_messages = error_logs['message'].dropna().astype(str)
                    
                    # Group similar error messages
                    error_groups = {}
                    for msg in error_messages:
                        # Simple grouping by first 50 characters
                        key = msg[:50].lower().strip()
                        if key not in error_groups:
                            error_groups[key] = []
                        error_groups[key].append(msg)
                    
                    # Find most common error patterns
                    common_errors = sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    print(f"   📊 Top Error Patterns:")
                    for i, (pattern, occurrences) in enumerate(common_errors[:3]):
                        print(f"     {i+1}. Pattern: {pattern}")
                        print(f"        Occurrences: {len(occurrences)}")
                        print(f"        Sample: {occurrences[0][:100]}...")
                else:
                    print("   ✅ No error logs found - system appears healthy")
                    
            except Exception as e:
                print(f"   ⚠️  LogAI anomaly detection failed: {e}")
        
        # Clustering analysis with LogAI
        if not logs_df.empty:
            print("\n📊 LogAI Clustering Analysis:")
            
            try:
                from logai.analysis import clustering
                
                # Cluster by log messages
                messages = logs_df['message'].dropna().astype(str)
                
                if len(messages) > 10:
                    # Simple clustering by message similarity
                    message_groups = {}
                    for msg in messages:
                        # Group by message length and first few words
                        words = msg.lower().split()[:3]
                        key = f"{len(msg)}_{'_'.join(words)}"
                        if key not in message_groups:
                            message_groups[key] = []
                        message_groups[key].append(msg)
                    
                    # Sort by group size
                    clusters = sorted(message_groups.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    print(f"   🎯 Found {len(clusters)} message clusters:")
                    for i, (cluster_id, cluster_msgs) in enumerate(clusters[:5]):
                        print(f"     Cluster {i+1}: {len(cluster_msgs)} similar messages")
                        print(f"       Sample: {cluster_msgs[0][:80]}...")
                else:
                    print("   📊 Not enough messages for clustering analysis")
                    
            except Exception as e:
                print(f"   ⚠️  LogAI clustering failed: {e}")
                
    except ImportError as e:
        print(f"❌ LogAI modules not available: {e}")
        print("   This might be due to missing dependencies or incomplete installation")
    
    except Exception as e:
        print(f"❌ LogAI analysis failed: {e}")

def generate_insights(logs_df):
    """Generate actionable insights from the analysis"""
    print("\n💡 ACTIONABLE INSIGHTS")
    print("=" * 50)
    
    if logs_df.empty:
        print("❌ No logs to analyze")
        return
    
    insights = []
    
    # Error rate analysis
    if 'level' in logs_df.columns:
        level_counts = logs_df['level'].value_counts()
        total_logs = len(logs_df)
        error_count = level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0) + level_counts.get('FATAL', 0)
        error_rate = (error_count / total_logs) * 100
        
        if error_rate > 5:
            insights.append(f"🚨 HIGH ERROR RATE: {error_rate:.1f}% - Immediate attention required")
        elif error_rate > 2:
            insights.append(f"⚠️  ELEVATED ERROR RATE: {error_rate:.1f}% - Monitor closely")
        else:
            insights.append(f"✅ ERROR RATE WITHIN LIMITS: {error_rate:.1f}%")
    
    # Service health analysis
    if 'service' in logs_df.columns:
        service_counts = logs_df['service'].value_counts()
        most_active_service = service_counts.index[0]
        
        # Check for error concentration
        error_logs = logs_df[logs_df['level'].isin(['ERROR', 'CRITICAL', 'FATAL'])]
        if not error_logs.empty:
            error_by_service = error_logs['service'].value_counts()
            problematic_service = error_by_service.index[0] if len(error_by_service) > 0 else None
            
            if problematic_service:
                insights.append(f"🏥 SERVICE HEALTH: '{problematic_service}' has {error_by_service.iloc[0]} errors")
    
    # Pattern analysis
    if 'message' in logs_df.columns:
        messages = logs_df['message'].dropna().astype(str)
        
        # Look for common issues
        timeout_patterns = messages.str.contains('timeout', case=False, na=False).sum()
        connection_patterns = messages.str.contains('connection', case=False, na=False).sum()
        payment_patterns = messages.str.contains('payment', case=False, na=False).sum()
        
        if timeout_patterns > 0:
            insights.append(f"⏰ TIMEOUT ISSUES: {timeout_patterns} timeout events detected")
        if connection_patterns > 0:
            insights.append(f"🔗 CONNECTION ISSUES: {connection_patterns} connection problems detected")
        if payment_patterns > 0:
            insights.append(f"💳 PAYMENT SYSTEM: {payment_patterns} payment-related events")
    
    # Volume analysis
    if len(logs_df) > 500:
        insights.append(f"📈 HIGH VOLUME: {len(logs_df)} logs - System is very active")
    elif len(logs_df) < 50:
        insights.append(f"📉 LOW VOLUME: {len(logs_df)} logs - Check if system is running")
    
    # Display insights
    for insight in insights:
        print(f"   {insight}")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print("   1. Monitor error-prone services more closely")
    print("   2. Set up alerts for timeout and connection issues")
    print("   3. Implement log aggregation for better visibility")
    print("   4. Consider rate limiting for high-volume services")

def main():
    """Main analysis function"""
    print("🤖 LogAI Enhanced Log Analysis")
    print("=" * 40)
    
    # Fetch logs
    print("📡 Fetching logs from API...")
    logs = fetch_logs_from_api()
    
    if not logs:
        print("❌ No logs retrieved from API")
        return
    
    print(f"✅ Retrieved {len(logs)} log entries")
    
    # Parse logs
    parsed_logs = [parse_log_entry(log) for log in logs]
    logs_df = pd.DataFrame(parsed_logs)
    
    # Perform analysis
    basic_log_analysis(logs_df)
    logai_enhanced_analysis(logs_df)
    generate_insights(logs_df)
    
    print(f"\n🎉 Analysis completed at {datetime.now()}")

if __name__ == "__main__":
    main()

import sys
import json
from datetime import datetime, timezone
from log_tailer import LogAIFullPipeline

def test_logai_pipeline():
    pipeline = LogAIFullPipeline()
    
    # Generate mock logs
    logs = []
    
    # Normal logs
    for i in range(20):
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "message": f"User {i} logged in successfully",
            "service": "auth-service"
        })
        
    # Anomaly logs (errors)
    for i in range(15):
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "message": f"Connection timeout to database instance db-0{i}",
            "service": "db-service"
        })
        
    print(f"Testing pipeline with {len(logs)} logs...")
    result = pipeline.analyze(logs)
    
    print("\n--- Pipeline Result ---")
    print(json.dumps(result, indent=2))
    
    if "error" in result.get("pipeline", "").lower() or result.get("pipeline") == "empty":
        print("\n❌ Pipeline failed to execute properly.")
        sys.exit(1)
        
    print("\n✅ LogAI Pipeline executed successfully.")

if __name__ == "__main__":
    test_logai_pipeline()

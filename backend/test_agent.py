import sys
import json
import logging
from unittest.mock import MagicMock
from agent_orchestrator import AgentOrchestrator

logging.basicConfig(level=logging.INFO)

def test_agent_orchestrator():
    # Mock DB manager
    db_mock = MagicMock()
    
    orchestrator = AgentOrchestrator(db_mock)
    
    # Check if MCP config was created
    if not orchestrator.mcp_config_path.exists():
        print("❌ MCP config file was not created.")
        sys.exit(1)
        
    print("✅ MCP config verified.")
    
    # Test context building
    trace_id = "test-trace-123"
    logs = [{"level": "ERROR", "message": "Test error"}]
    analysis = {"score": 0.9, "ts_anomaly": True, "error_rate": 0.5, "signals": [{"message": "Test error"}]}
    
    context = orchestrator._build_context(trace_id, logs, analysis, "test/repo", "main")
    if "test-trace-123" not in context or "Test error" not in context:
        print("❌ Context building failed.")
        sys.exit(1)
        
    print("✅ Context building verified.")
    print("\n--- Context Output ---")
    print(context)
    
    # We won't trigger the actual async run since it clones repos and calls Claude,
    # but we can verify the DB calls and methods exist.
    try:
        # Mock the run trigger
        res = orchestrator.trigger_async("mon-1", trace_id, logs, analysis, "test/repo", "token", "main")
        print(f"✅ Triggered async run with ID: {res}")
    except Exception as e:
        print(f"❌ Failed to trigger async run: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_agent_orchestrator()

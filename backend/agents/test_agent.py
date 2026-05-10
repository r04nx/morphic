#!/usr/bin/env python3
"""
Test script for Claude Code Agent with sample data
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the agents directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from claude_code_agent import ClaudeCodeAgentInvoker


async def test_rca_analysis():
    """Test RCA analysis with sample logs"""
    
    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY environment variable is not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return False
    
    print("🚀 Starting Claude Code Agent Test")
    print("=" * 50)
    
    try:
        # Use the sample logs and SRE prompt
        project_dir = "/home/rohan/Public/morphic"  # Current project
        system_prompt_file = "sre_system_prompt.txt"
        log_input = "sample_logs.txt"
        
        # Read system prompt
        with open(system_prompt_file, 'r') as f:
            system_prompt = f.read().strip()
        
        print(f"📁 Project Directory: {project_dir}")
        print(f"📝 System Prompt: {system_prompt_file}")
        print(f"📋 Log Input: {log_input}")
        print()
        
        # Initialize agent
        print("🔧 Initializing Claude Code Agent...")
        invoker = ClaudeCodeAgentInvoker(project_dir, system_prompt)
        
        # Perform RCA
        print("🔍 Performing Root Cause Analysis...")
        results = await invoker.perform_rca(log_input)
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 RCA ANALYSIS RESULTS")
        print("=" * 60)
        print(f"✅ Success: {results['success']}")
        
        if 'log_analysis' in results:
            log_analysis = results['log_analysis']
            print(f"📈 Total Errors: {log_analysis['total_errors']}")
            print(f"🔍 Error Patterns: {log_analysis['error_patterns']}")
            print(f"🎯 Affected Components: {log_analysis['affected_components']}")
            print(f"⏰ Timeline Entries: {len(log_analysis['timeline'])}")
        
        if results['error']:
            print(f"❌ Error: {results['error']}")
        
        # Save session
        invoker.save_session()
        print(f"\n💾 Session saved to agent_logs/")
        
        return results['success']
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


async def test_basic_functionality():
    """Test basic agent functionality without RCA"""
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY environment variable is not set")
        return False
    
    print("🧪 Testing Basic Agent Functionality")
    print("=" * 40)
    
    try:
        project_dir = "/home/rohan/Public/morphic"
        system_prompt_file = "example_system_prompt.txt"
        
        with open(system_prompt_file, 'r') as f:
            system_prompt = f.read().strip()
        
        invoker = ClaudeCodeAgentInvoker(project_dir, system_prompt)
        
        # Simple analysis task
        task = "Analyze the project structure and identify the main components of the Morphic system."
        print(f"📝 Task: {task}")
        
        results = await invoker.execute_task(task)
        
        print(f"✅ Success: {results['success']}")
        print(f"💬 Messages: {len(results['messages'])}")
        print(f"🔧 Tool calls: {len(results['tool_calls'])}")
        
        invoker.save_session()
        return results['success']
        
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False


async def main():
    """Main test runner"""
    
    print("🤖 Claude Code Agent Test Suite")
    print("=" * 50)
    print()
    
    # Test basic functionality first
    basic_success = await test_basic_functionality()
    print()
    
    # Test RCA analysis
    rca_success = await test_rca_analysis()
    print()
    
    # Summary
    print("=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    print(f"Basic Functionality: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"RCA Analysis: {'✅ PASS' if rca_success else '❌ FAIL'}")
    
    if basic_success and rca_success:
        print("\n🎉 All tests passed! The Claude Code Agent is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration and logs.")


if __name__ == "__main__":
    print("⚠️  SECURITY NOTE: Make sure to set your ANTHROPIC_API_KEY environment variable")
    print("   Never share API keys in chat or commit them to version control")
    print()
    
    asyncio.run(main())

#!/usr/bin/env python3
"""
Example usage of the Morphic Agents module
"""

import asyncio
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_orchestrator import AgentOrchestrator
from models import TaskPriority
from workflows import RCAWorkflow, CodeReviewWorkflow, IncidentResponseWorkflow
from result_processor import ResultProcessor, ResultAggregator


async def example_rca_workflow():
    """Example: RCA workflow with multiple log sources"""
    
    print("🔍 Starting RCA Workflow Example")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        max_concurrent_tasks=3,
        enable_rate_limiting=True,
        rate_limit_per_minute=5
    )
    
    # Initialize result processor
    result_processor = ResultProcessor()
    
    # Read system prompt
    with open("sre_system_prompt.txt", 'r') as f:
        system_prompt = f.read().strip()
    
    # Create RCA workflow
    rca_workflow = RCAWorkflow(orchestrator)
    
    # Sample log inputs
    log_inputs = [
        "sample_logs.txt",
        # Add more log files or direct log content as needed
    ]
    
    # Start orchestrator in background
    orchestrator_task = asyncio.create_task(orchestrator.start())
    
    try:
        # Execute RCA workflow
        workflow_result = await rca_workflow.execute(
            project_dir="/home/rohan/Public/morphic",
            system_prompt=system_prompt,
            log_inputs=log_inputs,
            concurrent=True
        )
        
        print(f"✅ RCA Workflow completed")
        print(f"Total tasks: {workflow_result['total_tasks']}")
        print(f"Successful tasks: {workflow_result['successful_tasks']}")
        
        # Process results
        successful_results = [
            result for result in workflow_result['results'].values() 
            if result.success
        ]
        
        if successful_results:
            processed_results = await result_processor.process_batch(successful_results)
            
            # Aggregate results
            aggregator = ResultAggregator()
            aggregated = aggregator.aggregate_results(processed_results)
            
            print("\n📊 Aggregated Results:")
            print(f"Summary: {aggregated['summary']}")
            print(f"Success Rate: {aggregated['statistics']['success_rate']:.2%}")
            print(f"Average Execution Time: {aggregated['statistics']['average_execution_time']:.1f}s")
            
            # Display top insights
            if aggregated['insights']:
                print("\n💡 Key Insights:")
                for insight in aggregated['insights'][:5]:
                    print(f"  • {insight}")
            
            # Display top recommendations
            if aggregated['recommendations']:
                print("\n🎯 Recommendations:")
                for rec in aggregated['recommendations'][:5]:
                    print(f"  • {rec}")
        
    finally:
        await orchestrator.stop()


async def example_incident_response():
    """Example: Complete incident response workflow"""
    
    print("\n🚨 Starting Incident Response Example")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(max_concurrent_tasks=2)
    
    # Read system prompt
    with open("sre_system_prompt.txt", 'r') as f:
        system_prompt = f.read().strip()
    
    # Create incident response workflow
    ir_workflow = IncidentResponseWorkflow(orchestrator)
    
    # Sample incident data
    incident_data = {
        'incident_id': 'INC-2024-001',
        'severity': 'HIGH',
        'logs': 'sample_logs.txt',
        'context': 'Payment processing failures during peak load',
        'affected_services': ['payment-service', 'order-service'],
        'start_time': '2024-05-10 10:15:00',
        'business_impact': 'Orders failing, revenue impact'
    }
    
    # Start orchestrator
    orchestrator_task = asyncio.create_task(orchestrator.start())
    
    try:
        # Execute incident response
        workflow_result = await ir_workflow.execute(
            project_dir="/home/rohan/Public/morphic",
            system_prompt=system_prompt,
            incident_data=incident_data,
            phases=['triage', 'rca', 'remediation']
        )
        
        print(f"✅ Incident Response completed")
        print(f"Overall Success: {workflow_result['overall_success']}")
        
        # Display phase results
        for phase, result in workflow_result['phase_results'].items():
            status = "✅" if result.get('success', False) else "❌"
            print(f"{status} {phase.title()}: {result.get('execution_time', 0):.1f}s")
        
    finally:
        await orchestrator.stop()


async def example_code_review():
    """Example: Code review workflow"""
    
    print("\n📝 Starting Code Review Example")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(max_concurrent_tasks=2)
    
    # Read system prompt
    with open("example_system_prompt.txt", 'r') as f:
        system_prompt = f.read().strip()
    
    # Create code review workflow
    cr_workflow = CodeReviewWorkflow(orchestrator)
    
    # Sample review tasks
    review_tasks = [
        {
            'name': 'security-review',
            'prompt': 'Review the codebase for security vulnerabilities and authentication issues'
        },
        {
            'name': 'performance-review',
            'prompt': 'Analyze the codebase for performance bottlenecks and optimization opportunities'
        },
        {
            'name': 'code-quality-review',
            'prompt': 'Review code quality, maintainability, and adherence to best practices'
        }
    ]
    
    # Start orchestrator
    orchestrator_task = asyncio.create_task(orchestrator.start())
    
    try:
        # Execute code review
        workflow_result = await cr_workflow.execute(
            project_dir="/home/rohan/Public/morphic",
            system_prompt=system_prompt,
            review_tasks=review_tasks,
            concurrent=True
        )
        
        print(f"✅ Code Review completed")
        print(f"Total reviews: {workflow_result['total_tasks']}")
        print(f"Successful reviews: {workflow_result['successful_tasks']}")
        
    finally:
        await orchestrator.stop()


async def example_mixed_workload():
    """Example: Mixed workload with different task types"""
    
    print("\n🔄 Starting Mixed Workload Example")
    print("=" * 50)
    
    # Initialize orchestrator with callbacks
    orchestrator = AgentOrchestrator(max_concurrent_tasks=4)
    
    # Add event callbacks
    def on_task_started(task):
        print(f"🚀 Task started: {task.name}")
    
    def on_task_completed(task, result):
        print(f"✅ Task completed: {task.name} ({result.execution_time:.1f}s)")
    
    def on_task_failed(task, error):
        print(f"❌ Task failed: {task.name} - {error}")
    
    orchestrator.add_callback('task_started', on_task_started)
    orchestrator.add_callback('task_completed', on_task_completed)
    orchestrator.add_callback('task_failed', on_task_failed)
    
    # Start orchestrator
    orchestrator_task = asyncio.create_task(orchestrator.start())
    
    try:
        # Add different types of tasks
        tasks = []
        
        # RCA task
        with open("sre_system_prompt.txt", 'r') as f:
            sre_prompt = f.read().strip()
        
        rca_task_id = orchestrator.add_rca_task(
            name="production-rca",
            project_dir="/home/rohan/Public/morphic",
            system_prompt=sre_prompt,
            log_input="sample_logs.txt",
            priority=TaskPriority.HIGH
        )
        tasks.append(rca_task_id)
        
        # Code review task
        with open("example_system_prompt.txt", 'r') as f:
            dev_prompt = f.read().strip()
        
        review_task_id = orchestrator.add_code_review_task(
            name="architecture-review",
            project_dir="/home/rohan/Public/morphic",
            system_prompt=dev_prompt,
            task_prompt="Review the system architecture and suggest improvements",
            priority=TaskPriority.MEDIUM
        )
        tasks.append(review_task_id)
        
        # Wait for all tasks
        results = await orchestrator.wait_for_all_tasks(timeout=600)
        
        # Display statistics
        stats = orchestrator.get_statistics()
        print(f"\n📈 Final Statistics:")
        print(f"Total Tasks: {stats['total_tasks']}")
        print(f"Success Rate: {stats['success_rate']:.2%}")
        print(f"Average Execution Time: {stats['average_execution_time']:.1f}s")
        
    finally:
        await orchestrator.stop()


async def main():
    """Main function to run examples"""
    
    print("🤖 Morphic Agents Module Examples")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY environment variable is not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    try:
        # Run examples
        await example_rca_workflow()
        await example_incident_response()
        await example_code_review()
        await example_mixed_workload()
        
        print("\n🎉 All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

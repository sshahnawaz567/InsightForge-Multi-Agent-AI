"""
Week 3 Integration Test
Test complete workflow with Calculation Agent + Executor
"""
import asyncio
import sys
sys.path.append('..')

from backend.agents.query_understanding_agent import QueryUnderstandingAgent
from backend.agents.planning_agent import PlanningAgent
from backend.agents.sql_generation_agent import SQLGenerationAgent
from backend.agents.calculation_agent import CalculationAgent
from backend.agents.workflow_executor import WorkflowExecutor
from backend.config.settings import settings

async def test_root_cause_analysis():
    """
    Test: "Why did revenue drop in December?"
    
    Should:
    1. Parse query
    2. Create multi-step plan
    3. Execute plan automatically
    4. Calculate changes
    5. Return insights
    """
    
    print("="*70)
    print("WEEK 3: ROOT CAUSE ANALYSIS TEST")
    print("="*70)
    
    # Initialize agents
    query_agent = QueryUnderstandingAgent(settings.OPENAI_API_KEY)
    planning_agent = PlanningAgent(settings.OPENAI_API_KEY)
    sql_agent = SQLGenerationAgent(
        settings.OPENAI_API_KEY,
        settings.DATABASE_URL
    )
    calc_agent = CalculationAgent()
    
    await sql_agent.initialize()
    
    # Create agent registry for executor
    agent_registry = {
        'sql_generation': sql_agent,
        'calculation': calc_agent
    }
    
    executor = WorkflowExecutor(agent_registry)
    
    # Test query
    query = "Compare December 2024 vs November 2024 revenue"
    
    print(f"\n🔍 Query: '{query}'\n")
    
    # Step 1: Parse query
    print("STEP 1: Query Understanding")
    print("-"*70)
    result = await query_agent.run({'query': query})
    parsed_query = result['result']['parsed_query']
    print(f"✅ Parsed: {parsed_query['query_type']}")
    
    # Step 2: Create plan
    print(f"\nSTEP 2: Planning")
    print("-"*70)
    result = await planning_agent.run({'parsed_query': parsed_query})
    plan = result['result']['plan']
    print(f"✅ Created {len(plan['steps'])}-step plan")
    
    # Step 3: Execute workflow
    print(f"\nSTEP 3: Workflow Execution")
    print("-"*70)
    workflow_result = await executor.execute(plan)
    
    # Display results
    print(f"\n{'='*70}")
    print("RESULTS")
    print('='*70)
    
    for step_num, step_result in workflow_result['step_results'].items():
        if step_result['status'] == 'success':
            print(f"\nStep {step_num}: {step_result['agent_id']}")
            
            if step_result['agent_id'] == 'calculation':
                calc_result = step_result['result']
                print(f"  Current:    ${calc_result['current_value']:,.2f}")
                print(f"  Comparison: ${calc_result['comparison_value']:,.2f}")
                print(f"  Change:     {calc_result['percentage_change']:+.1f}%")
                print(f"  Status:     {calc_result['interpretation']}")
    
    # Cleanup
    await sql_agent.close()

async def test_cache_performance():
    """Test caching improves performance"""
    
    print("\n" + "="*70)
    print("CACHE PERFORMANCE TEST")
    print("="*70)
    
    sql_agent = SQLGenerationAgent(
        settings.OPENAI_API_KEY,
        settings.DATABASE_URL
    )
    
    await sql_agent.initialize()
    
    # Same query twice
    query_input = {
        'task': 'fetch_data',
        'params': {
            'metrics': ['revenue'],
            'time_period': {'type': 'relative', 'start': 'last_month', 'end': 'last_month'}
        }
    }
    
    # First call (cache miss)
    print("\n🔍 First call (no cache):")
    result1 = await sql_agent.run(query_input)
    time1 = result1['execution_time']
    print(f"   Time: {time1}s")
    
    # Second call (cache hit)
    print("\n✨ Second call (cached):")
    result2 = await sql_agent.run(query_input)
    time2 = result2['execution_time']
    print(f"   Time: {time2}s")
    
    speedup = ((time1 - time2) / time1) * 100
    print(f"\n🚀 Speedup: {speedup:.0f}% faster with cache!")
    
    # Cache stats
    stats = sql_agent.cache.get_stats()
    print(f"\n📊 Cache stats:")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Keys: {stats['keys']}")
    
    await sql_agent.close()

if __name__ == '__main__':
    print("\n🧪 Running root cause analysis test...\n")
    asyncio.run(test_root_cause_analysis())
    
    print("\n\n🧪 Running cache performance test...\n")
    asyncio.run(test_cache_performance())
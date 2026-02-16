"""
Week 2 Integration Test
Test Query Understanding → Planning → SQL Generation
"""
import asyncio
import sys
sys.path.append('..')

from backend.agents.query_understanding_agent import QueryUnderstandingAgent
from backend.agents.planning_agent import PlanningAgent
from backend.agents.sql_generation_agent import SQLGenerationAgent
from backend.config.settings import settings

async def test_end_to_end():
    """Test complete flow"""
    
    print("="*70)
    print("WEEK 2 INTEGRATION TEST")
    print("="*70)
    
    # Validate settings
    settings.validate()
    
    # Initialize agents
    print("\n📦 Initializing agents...")
    
    query_agent = QueryUnderstandingAgent(settings.OPENAI_API_KEY)
    planning_agent = PlanningAgent(settings.OPENAI_API_KEY)
    sql_agent = SQLGenerationAgent(
        settings.OPENAI_API_KEY,
        settings.DATABASE_URL
    )
    
    await sql_agent.initialize()
    
    print("✅ All agents initialized\n")
    
    # Test query
    test_query = "What was our total revenue last month?"
    
    print(f"🔍 User Query: '{test_query}'\n")
    print("="*70)
    
    # Step 1: Query Understanding
    print("\n🤖 STEP 1: Query Understanding Agent")
    print("-"*70)
    
    result1 = await query_agent.run({'query': test_query})
    
    if result1['status'] != 'success':
        print(f"❌ Failed: {result1.get('error')}")
        return
    
    parsed_query = result1['result']['parsed_query']
    print(f"✅ Parsed successfully")
    print(f"   Query Type: {parsed_query['query_type']}")
    print(f"   Metrics: {parsed_query['metrics']}")
    print(f"   Time Period: {parsed_query['time_period']}")
    print(f"   Confidence: {parsed_query['confidence']}")
    print(f"   Time: {result1['execution_time']}s")
    
    # Step 2: Planning
    print("\n🤖 STEP 2: Planning Agent")
    print("-"*70)
    
    result2 = await planning_agent.run({'parsed_query': parsed_query})
    
    if result2['status'] != 'success':
        print(f"❌ Failed: {result2.get('error')}")
        return
    
    plan = result2['result']['plan']
    print(f"✅ Plan created")
    print(f"   Plan ID: {plan['plan_id']}")
    print(f"   Steps: {len(plan['steps'])}")
    print(f"   Estimated time: {result2['result']['estimated_time']}s")
    print(f"\n   Execution Steps:")
    for step in plan['steps']:
        print(f"     {step['step']}. {step['agent']} → {step['task']}")
    print(f"   Time: {result2['execution_time']}s")
    
    # Step 3: Execute Plan (SQL Generation)
    print("\n🤖 STEP 3: SQL Generation Agent")
    print("-"*70)
    
    # Execute first step of plan (the SQL fetch)
    first_step = plan['steps'][0]
    
    result3 = await sql_agent.run({
        'task': first_step['task'],
        'params': first_step['params']
    })
    
    if result3['status'] != 'success':
        print(f"❌ Failed: {result3.get('error')}")
        await sql_agent.close()
        return
    
    sql_result = result3['result']
    print(f"✅ SQL executed successfully")
    print(f"   Rows returned: {sql_result['row_count']}")
    print(f"   Time: {result3['execution_time']}s")
    
    print(f"\n   Generated SQL:")
    print(f"   {'-'*66}")
    for line in sql_result['sql'].split('\n'):
        print(f"   {line}")
    print(f"   {'-'*66}")
    
    # Show results
    if sql_result['results']:
        print(f"\n   📊 Results:")
        for row in sql_result['results'][:5]:  # Show first 5 rows
            print(f"      {row}")
        if sql_result['row_count'] > 5:
            print(f"      ... ({sql_result['row_count'] - 5} more rows)")
    
    # Final summary
    print("\n" + "="*70)
    print("✅ END-TO-END TEST COMPLETE")
    print("="*70)
    
    total_time = (result1['execution_time'] + 
                  result2['execution_time'] + 
                  result3['execution_time'])
    
    print(f"\n📈 Performance Summary:")
    print(f"   Query Understanding: {result1['execution_time']}s")
    print(f"   Planning:            {result2['execution_time']}s")
    print(f"   SQL Generation:      {result3['execution_time']}s")
    print(f"   " + "-"*40)
    print(f"   Total Time:          {round(total_time, 2)}s")
    
    print(f"\n🎯 Final Answer:")
    if sql_result['results']:
        # Format the answer nicely
        result_row = sql_result['results'][0]
        if 'revenue' in result_row or 'sum' in str(result_row).lower():
            revenue_key = next(k for k in result_row.keys() if 'sum' in k.lower() or 'revenue' in k.lower())
            revenue = result_row[revenue_key]
            print(f"   💰 Total revenue last month: ${revenue:,.2f}")
    
    # Cleanup
    await sql_agent.close()

async def test_multiple_queries():
    """Test different query types"""
    
    print("\n" + "="*70)
    print("TESTING MULTIPLE QUERY TYPES")
    print("="*70)
    
    queries = [
        "What was revenue last month?",
        "Show me revenue by product category",
        "Compare December vs November revenue",
    ]
    
    query_agent = QueryUnderstandingAgent(settings.OPENAI_API_KEY)
    planning_agent = PlanningAgent(settings.OPENAI_API_KEY)
    sql_agent = SQLGenerationAgent(
        settings.OPENAI_API_KEY,
        settings.DATABASE_URL
    )
    
    await sql_agent.initialize()
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {query}")
        print('='*70)
        
        # Parse
        result = await query_agent.run({'query': query})
        if result['status'] != 'success':
            print(f"❌ Failed to parse")
            continue
        
        parsed = result['result']['parsed_query']
        
        # Plan
        result = await planning_agent.run({'parsed_query': parsed})
        if result['status'] != 'success':
            print(f"❌ Failed to plan")
            continue
        
        plan = result['result']['plan']
        print(f"✅ Created {len(plan['steps'])}-step plan ({plan['query_type']})")
        
        for step in plan['steps']:
            print(f"   {step['step']}. {step['agent']} → {step['task']}")
    
    await sql_agent.close()
    print("\n" + "="*70)

if __name__ == '__main__':
    print("\nRunning main end-to-end test...\n")
    asyncio.run(test_end_to_end())
    
    print("\n\nRunning multiple query types test...\n")
    asyncio.run(test_multiple_queries())
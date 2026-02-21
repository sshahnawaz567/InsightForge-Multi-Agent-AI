"""
Week 4 Integration Test - LangGraph Complete Workflow
Test all 6 agents working together autonomously
"""
import asyncio
import sys
sys.path.append('..')

from backend.agents.langgraph_workflow import InsightForgeWorkflow
from backend.config.settings import settings

async def test_simple_query():
    """Test simple lookup query"""
    
    print("\n" + "="*70)
    print("TEST 1: SIMPLE QUERY")
    print("="*70)
    
    workflow = InsightForgeWorkflow(
        openai_api_key=settings.OPENAI_API_KEY,
        database_url=settings.DATABASE_URL
    )
    
    query = "What was our revenue last month?"
    
    result = await workflow.run(query)
    
    # Display results
    print("\n📊 RESULTS:")
    print(f"   Query Type: {result['query_type']}")
    print(f"   SQL Queries: {len(result['sql_queries'])}")
    
    if result['sql_results']:
        print(f"   Answer: ${result['sql_results'][0]['results'][0].get('sum', 0):,.2f}")

async def test_root_cause_analysis():
    """Test complex root cause analysis"""
    
    print("\n" + "="*70)
    print("TEST 2: ROOT CAUSE ANALYSIS")
    print("="*70)
    
    workflow = InsightForgeWorkflow(
        openai_api_key=settings.OPENAI_API_KEY,
        database_url=settings.DATABASE_URL
    )
    
    query = "Why did revenue drop in December 2024?"
    
    result = await workflow.run(query)
    
    # Display full analysis
    print("\n" + "="*70)
    print("📊 COMPLETE ANALYSIS")
    print("="*70)
    
    print(f"\n📈 Metric Change:")
    if result['calculations']:
        calc = result['calculations']
        print(f"   Current:    ${calc['current_value']:,.2f}")
        print(f"   Previous:   ${calc['comparison_value']:,.2f}")
        print(f"   Change:     {calc['percentage_change']:+.1f}%")
        print(f"   Status:     {calc['interpretation']}")
    
    print(f"\n🔍 External Factors Found: {len(result['external_factors'])}")
    for factor in result['external_factors'][:3]:
        print(f"   [{factor['impact'].upper()}] {factor['content'][:80]}...")
    
    if result['executive_summary']:
        print(f"\n📝 Executive Summary:")
        print(f"   {result['executive_summary']}")
    
    if result['key_findings']:
        print(f"\n🎯 Key Findings:")
        for finding in result['key_findings']:
            print(f"   • {finding}")
    
    if result['root_causes']:
        print(f"\n🔎 Root Causes:")
        for i, cause in enumerate(result['root_causes'], 1):
            print(f"   {i}. [{cause['impact'].upper()}] {cause['cause']}")
            print(f"      {cause['explanation']}")
    
    if result['recommendations']:
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"   {i}. [{rec['priority'].upper()}] {rec['action']}")
            print(f"      {rec['rationale']}")
    
    print(f"\n⏱️  Performance:")
    for agent, time_taken in result['execution_times'].items():
        print(f"   {agent:20s}: {time_taken:.2f}s")
    print(f"   {'Total':20s}: {result['total_time']:.2f}s")

async def test_comparison():
    """Test period comparison"""
    
    print("\n" + "="*70)
    print("TEST 3: COMPARISON QUERY")
    print("="*70)
    
    workflow = InsightForgeWorkflow(
        openai_api_key=settings.OPENAI_API_KEY,
        database_url=settings.DATABASE_URL
    )
    
    query = "Compare December 2024 vs November 2024 revenue"
    
    result = await workflow.run(query)
    
    print("\n📊 Comparison Results:")
    if result['calculations']:
        calc = result['calculations']
        print(f"   December:  ${calc['current_value']:,.2f}")
        print(f"   November:  ${calc['comparison_value']:,.2f}")
        print(f"   Change:    {calc['percentage_change']:+.1f}% ({calc['direction']})")

    # ✅ ADD CLEANUP:
    await workflow.agents['sql'].close()

if __name__ == '__main__':
    print("\n🧪 Running LangGraph Integration Tests\n")
    
    asyncio.run(test_simple_query())
    asyncio.run(test_comparison())
    asyncio.run(test_root_cause_analysis())
    
    print("\n✅ All tests complete!\n")
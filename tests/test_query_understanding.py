"""
Test Query Understanding Agent
"""
import asyncio
import sys
sys.path.append('..')

from backend.agents.query_understanding_agent import QueryUnderstandingAgent
from backend.config.settings import settings

async def test_queries():
    """Test various query types"""
    
    # Validate config
    settings.validate()
    
    # Create agent
    agent = QueryUnderstandingAgent(
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    # Test queries
    test_cases = [
        "What was our revenue last month?",
        "Why did sales drop in December?",
        "Show me revenue by product category",
        "Compare Q4 2024 vs Q3 2024 revenue",
        "Which region has best sales?",
        "Predict next month's revenue",
        "Is there correlation between region and product category?",
        "What's trending?",  # Vague query
    ]
    
    print("="*70)
    print("TESTING QUERY UNDERSTANDING AGENT")
    print("="*70 + "\n")
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {query}")
        print('='*70)
        
        result = await agent.run({'query': query})
        
        if result['status'] == 'success':
            parsed = result['result']['parsed_query']
            print(f"\n✅ Status: {result['result']['status']}")
            print(f"📊 Query Type: {parsed['query_type']}")
            print(f"📈 Metrics: {parsed['metrics']}")
            print(f"📅 Time Period: {parsed['time_period']}")
            print(f"🎯 Confidence: {parsed['confidence']}")
            
            if parsed.get('ambiguities'):
                print(f"⚠️  Ambiguities: {parsed['ambiguities']}")
            
            if result['result']['status'] == 'needs_clarification':
                print(f"\n❓ Clarification needed:")
                for q in result['result']['clarification_questions']:
                    print(f"   - {q}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")
        
        print(f"\n⏱️  Execution time: {result['execution_time']}s")
    
    # Print metrics
    print(f"\n{'='*70}")
    print("AGENT METRICS")
    print('='*70)
    metrics = agent.get_metrics()
    for key, value in metrics.items():
        print(f"{key:25s}: {value}")

if __name__ == '__main__':
    asyncio.run(test_queries())
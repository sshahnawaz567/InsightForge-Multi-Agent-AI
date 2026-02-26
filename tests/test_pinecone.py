"""
Test Pinecone Integration
"""
import asyncio
import sys
sys.path.append('..')

from backend.agents.context_agent import ContextAgent
from backend.config.settings import settings

async def test_pinecone_search():
    """Test Context Agent with Pinecone"""
    
    print("="*70)
    print("🧪 TESTING PINECONE INTEGRATION")
    print("="*70)
    
    # Create context agent
    context_agent = ContextAgent()
    
    # Simulate calculation results (revenue dropped 79%)
    dependency_results = {
        1: {
            'status': 'success',
            'result': {
                'percentage_change': -79.3,
                'direction': 'decrease',
                'current_value': 300329.56,
                'comparison_value': 1454671.87
            }
        }
    }
    
    # Search for factors
    result = await context_agent.run({
        'task': 'search_external_factors',
        'params': {'time_period': {'start': '2024-12-01'}},
        'dependency_results': dependency_results
    })
    
    if result['status'] == 'success':
        data = result['result']
        
        print(f"\n✅ Search Method: {data['search_method']}")
        print(f"📊 Factors Found: {data['factors_found']}")
        print(f"🔍 Search Query: {data['search_query']}")
        
        print(f"\n🎯 Top Factors:")
        for i, factor in enumerate(data['factors'][:3], 1):
            print(f"\n{i}. [{factor['impact'].upper()}] {factor['category']}")
            print(f"   Score: {factor['relevance_score']}")
            print(f"   {factor['content'][:100]}...")
            print(f"   Source: {factor['source']}")
        
        print(f"\n📂 By Category:")
        for category, factors in data['by_category'].items():
            print(f"   {category}: {len(factors)} factors")
    
    else:
        print(f"❌ Search failed: {result.get('error')}")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    asyncio.run(test_pinecone_search())
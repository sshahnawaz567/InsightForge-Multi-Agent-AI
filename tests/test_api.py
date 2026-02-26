"""
Test FastAPI Endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    
    print(f"Status: {data['status']}")
    print(f"Components:")
    for component, status in data['components'].items():
        print(f"  {component}: {status}")
    
    assert response.status_code == 200
    assert data['status'] in ['healthy', 'degraded']
    print("✅ Health check passed")

def test_simple_query():
    """Test simple query"""
    print("\n" + "="*70)
    print("TEST 2: Simple Query")
    print("="*70)
    
    payload = {
        "query": "What was revenue last month?",
        "user_id": "test_user"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json=payload,
        timeout=30
    )
    
    data = response.json()
    
    print(f"Query ID: {data['query_id']}")
    print(f"Status: {data['status']}")
    print(f"Query Type: {data['query_type']}")
    print(f"Execution Time: {data['execution_time']}s")
    print(f"Agents: {data['agents_executed']}")
    
    assert response.status_code == 200
    assert data['status'] == 'success'
    print("✅ Simple query passed")

def test_complex_analysis():
    """Test complex root cause analysis"""
    print("\n" + "="*70)
    print("TEST 3: Complex Analysis")
    print("="*70)
    
    payload = {
        "query": "Why did revenue drop in December 2024?"
    }
    
    print("Sending query (this may take 20-30s)...")
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json=payload,
        timeout=60
    )
    
    data = response.json()
    
    print(f"\nQuery ID: {data['query_id']}")
    print(f"Status: {data['status']}")
    print(f"Execution Time: {data['execution_time']}s")
    
    if data['executive_summary']:
        print(f"\n📝 Executive Summary:")
        print(f"   {data['executive_summary'][:200]}...")
    
    if data['key_findings']:
        print(f"\n🎯 Key Findings:")
        for finding in data['key_findings'][:3]:
            print(f"   • {finding}")
    
    if data['root_causes']:
        print(f"\n🔎 Root Causes:")
        for cause in data['root_causes'][:2]:
            print(f"   [{cause['impact'].upper()}] {cause['cause']}")
    
    if data['external_factors']:
        print(f"\n🔍 External Factors Found: {len(data['external_factors'])}")
    
    assert response.status_code == 200
    assert data['status'] in ['success', 'partial']
    print("\n✅ Complex analysis passed")

def test_metrics():
    """Test metrics endpoint"""
    print("\n" + "="*70)
    print("TEST 4: System Metrics")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/metrics")
    data = response.json()
    
    print(f"Total Queries: {data['total_queries']}")
    print(f"Avg Execution Time: {data['avg_execution_time']}s")
    print(f"Cache Hit Rate: {data['cache_hit_rate']}%")
    
    print(f"\nAgent Performance:")
    for agent, metrics in data['agents_performance'].items():
        print(f"  {agent}:")
        print(f"    Executions: {metrics['total_executions']}")
        print(f"    Success Rate: {metrics['success_rate']}%")
        print(f"    Avg Time: {metrics['avg_time']}s")
    
    assert response.status_code == 200
    print("✅ Metrics test passed")

def test_examples():
    """Test examples endpoint"""
    print("\n" + "="*70)
    print("TEST 5: Example Queries")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/examples")
    data = response.json()
    
    print("Simple Queries:")
    for q in data['simple_queries']:
        print(f"  • {q}")
    
    print("\nAnalysis Queries:")
    for q in data['analysis_queries'][:3]:
        print(f"  • {q}")
    
    assert response.status_code == 200
    print("✅ Examples test passed")

if __name__ == '__main__':
    print("\n🧪 TESTING INSIGHTFORGE API")
    print("="*70)
    print("Make sure server is running: python backend/main.py")
    print("="*70)
    
    try:
        test_health()
        test_simple_query()
        test_examples()
        test_metrics()
        test_complex_analysis()  # This one takes longest
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
"""
Seed Pinecone with initial knowledge base
Run this once to populate vector DB with business context
"""
import asyncio
import sys
sys.path.append('..')

from tools.pinecone_manager import PineconeManager
from config.settings import settings

#Initial knowledge base docuemnts
# Initial knowledge base documents
KNOWLEDGE_BASE = [
    {
        'id': 'kb_seasonal_001',
        'content': 'December retail sales typically drop 10-15% due to holiday store closures and reduced business days. This is a normal seasonal pattern observed across most retail sectors.',
        'metadata': {
            'category': 'seasonal',
            'impact': 'expected',
            'source': 'Historical Analysis',
            'date': '2024-12-01'
        }
    },
    {
        'id': 'kb_competition_001',
        'content': 'Major competitor TechCorp launched aggressive pricing campaign on December 1st 2024, offering 40% discounts on enterprise plans. Campaign specifically targeted our existing customer base with matching feature set at significantly lower prices.',
        'metadata': {
            'category': 'competition',
            'impact': 'high',
            'source': 'Market Intelligence',
            'date': '2024-12-01'
        }
    },
    {
        'id': 'kb_logistics_001',
        'content': 'Shipping carriers (FedEx, UPS, DHL) experienced significant delays in Europe during December 2024 due to winter weather conditions and peak holiday volume. Average delivery times increased by 3-5 days.',
        'metadata': {
            'category': 'logistics',
            'impact': 'medium',
            'source': 'Industry Report',
            'date': '2024-12-15'
        }
    },
    {
        'id': 'kb_seasonal_002',
        'content': 'Black Friday (November 29th 2024) drove 200% revenue spike in late November, creating unusually high comparison baseline. Post-Black Friday periods typically show 20-30% decline as customers reduce spending.',
        'metadata': {
            'category': 'seasonal',
            'impact': 'medium',
            'source': 'Internal Data',
            'date': '2024-11-29'
        }
    },
    {
        'id': 'kb_regulatory_001',
        'content': 'New data privacy regulations in EU effective December 1st 2024 impacted digital marketing tracking and retargeting campaigns. Many companies reported 15-25% reduction in ad effectiveness due to cookie restrictions.',
        'metadata': {
            'category': 'regulatory',
            'impact': 'low',
            'source': 'Legal Team',
            'date': '2024-12-01'
        }
    },
    {
        'id': 'kb_product_001',
        'content': 'Product launch delay in Q4 2024 pushed new feature release from November to January. Customer expectations were set for November launch, causing disappointment and some churn among enterprise customers waiting for these features.',
        'metadata': {
            'category': 'product',
            'impact': 'medium',
            'source': 'Product Team',
            'date': '2024-11-15'
        }
    },
    {
        'id': 'kb_economy_001',
        'content': 'Economic indicators showed consumer confidence declining 8% in Q4 2024 due to inflation concerns. Consumer discretionary spending decreased, particularly in technology and non-essential purchases.',
        'metadata': {
            'category': 'economy',
            'impact': 'medium',
            'source': 'Economic Research',
            'date': '2024-10-01'
        }
    },
    {
        'id': 'kb_marketing_001',
        'content': 'Marketing budget was reduced by 30% in December 2024 due to year-end cost optimization. This resulted in lower ad spend, reduced campaign reach, and decreased new customer acquisition.',
        'metadata': {
            'category': 'marketing',
            'impact': 'high',
            'source': 'Marketing Team',
            'date': '2024-12-01'
        }
    },
    {

        'id': 'kb_support_001',
        'content': 'Customer support response times increased from 2 hours to 6 hours average in December due to holiday staffing shortages. Customer satisfaction scores dropped from 4.5 to 3.8 stars, potentially contributing to churn.',
        'metadata': {
            'category': 'support',
            'impact': 'medium',
            'source': 'Support Team',
            'date': '2024-12-10'
        }
    },
    {
        'id': 'kb_technical_001',
        'content': 'System outage on December 3rd 2024 lasting 4 hours affected 30% of users during peak business hours. Outage was caused by database failure and resulted in lost transactions and customer complaints.',
        'metadata': {
            'category': 'technical',
            'impact': 'high',
            'source': 'Engineering Team',
            'date': '2024-12-03'
        }
    }
]

def seed_knowledge_base():
    """Seed Pinecone with initial knowledge"""
    
    print("="*70)
    print("🌱 SEEDING PINECONE KNOWLEDGE BASE")
    print("="*70)
    
    # Validate settings
    if not settings.PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set in .env")
        return
    
    # Initialize Pinecone
    pm = PineconeManager(
        api_key=settings.PINECONE_API_KEY,
        index_name=settings.PINECONE_INDEX_NAME
    )

    # Optional: Clear existing data
    # pm.delete_all(namespace="knowledge_base")

    #Upset documents
    count = pm.upsert_documents(
        documents=KNOWLEDGE_BASE,
        namespace="knowledge_base"
    )

    print(f"\n✅ Seeded {count} documents to Pinecone")
    
    # Test search
    print("\n🔍 Testing search...")
    results = pm.search(
        query="Why did revenue drop?",
        top_k=3,
        namespace="knowledge_base"
    )

    print(f"\nTop 3 results for 'Why did revenue drop?':")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Category: {result['metadata'].get('category')}")
        print(f"   Content: {result['content'][:100]}...")
    
    # Show stats
    stats = pm.get_stats()
    print(f"\n📊 Index Stats:")
    print(f"   Total vectors: {stats.get('total_vectors', 0)}")
    print(f"   Dimension: {stats.get('dimension', 0)}")
    
    print("\n" + "="*70)
    print("✅ Seeding complete!")
    print("="*70)

if __name__ == '__main__':
    seed_knowledge_base()
"""
Seed script for Docker container
Connects to postgres service by name
"""
import asyncio
import asyncpg
from generate_data import generate_customers, generate_orders, add_realistic_patterns

async def main():
    print("🌱 Starting database seeding...")
    
    # Connect using Docker service name
    conn = await asyncpg.connect(
        'postgresql://postgres:insightforge_password@postgres:5432/insightforge'
    )
    
    try:
        # Check if already seeded
        count = await conn.fetchval('SELECT COUNT(*) FROM orders')
        
        if count > 0:
            print(f"ℹ️  Database already has {count} orders, skipping")
            return
        
        # Generate data
        await generate_customers(conn)
        await generate_orders(conn)
        await add_realistic_patterns(conn)
        
        # Verify
        order_count = await conn.fetchval('SELECT COUNT(*) FROM orders')
        customer_count = await conn.fetchval('SELECT COUNT(*) FROM customers')
        
        print(f"\n✅ Seeding complete!")
        print(f"   Orders: {order_count}")
        print(f"   Customers: {customer_count}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
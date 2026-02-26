"""
Seed database in Docker environment
Waits for database to be ready, then generates data
"""
import asyncio
import sys
import time
sys.path.append('/app')

import asyncpg
from backend.database.generate_data import generate_customers, generate_orders, add_realistic_patterns

async def wait_for_db(max_retries=30):
    """Wait for PostgreSQL to be ready"""

    db_url = "postgresql://postgres:12345@postgres:5432/insightforge"

    for i in range(max_retries):
        try:
            conn = await asyncpg.connect(db_url)
            await conn.close()
            print("✅ Database is ready!")
            return True
        except Exception as e:
            print(f"⏳ Waiting for database... ({i+1}/{max_retries})")
            await asyncio.sleep(2)

    print("❌ Database not ready after 60 seconds")
    return False

async def seed():
    """Seed database with data"""

    # Wait for database
    if not await wait_for_db():
        return
    
    db_url = "postgresql://postgres:12345@postgres:5432/insightforge"

    print("\n🌱 Starting database seeding...")
    
    conn = await asyncpg.connect(db_url)

    try:
        # Check if already seeded
        count = await conn.fetchval('SELECT COUNT(*) FROM orders')

        if count > 0:
            print(f"ℹ️  Database already has {count} orders, skipping seed")
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
    asyncio.run(seed())
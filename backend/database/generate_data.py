"""
Generate 50,000 realistic e-commerce orders for demo
"""
import asyncio
import asyncpg
from faker import Faker
import random
from datetime import datetime, timedelta
from decimal import Decimal

fake = Faker()

# Configuration
NUM_CUSTOMERS = 5000
NUM_ORDERS = 50000

# Realistic product catalog
PRODUCTS = {
    'Electronics': [
        ('MacBook Pro', 1500, 2500),
        ('iPhone 15', 800, 1200),
        ('AirPods Pro', 200, 300),
        ('iPad Air', 500, 800),
        ('Samsung TV', 600, 1500),
    ],
    'Clothing': [
        ('Winter Jacket', 80, 200),
        ('Running Shoes', 60, 150),
        ('Jeans', 40, 100),
        ('T-Shirt', 15, 40),
        ('Dress', 50, 150),
    ],
    'Home & Garden': [
        ('Coffee Maker', 50, 200),
        ('Vacuum Cleaner', 100, 400),
        ('Bed Sheets', 30, 100),
        ('Kitchen Knife Set', 40, 150),
        ('Plant Pot', 10, 50),
    ],
    'Books': [
        ('Fiction Novel', 10, 30),
        ('Cookbook', 15, 40),
        ('Programming Book', 30, 80),
        ('Biography', 12, 35),
        ('Children Book', 8, 20),
    ]
}

REGIONS = ['North America', 'Europe', 'Asia', 'South America', 'Australia']
PAYMENT_METHODS = ['Credit Card', 'Debit Card', 'PayPal', 'Apple Pay']
STATUSES = ['completed', 'pending', 'cancelled', 'refunded']
SEGMENTS = ['Individual', 'SMB', 'Enterprise']

async def generate_customers(conn):
    """Generate customer data"""
    print("Generating customers...")
    
    customers = []
    for i in range(NUM_CUSTOMERS):
        customer = (
            fake.name(),
            fake.email(),
            fake.date_between(start_date='-5y', end_date='today'),
            random.choice(SEGMENTS),
            random.choice(REGIONS)
        )
        customers.append(customer)
    
    # Bulk insert
    await conn.executemany('''
        INSERT INTO customers (customer_name, email, signup_date, customer_segment, country)
        VALUES ($1, $2, $3, $4, $5)
    ''', customers)
    
    print(f"✅ Created {NUM_CUSTOMERS} customers")

async def generate_orders(conn):
    """Generate order data with realistic patterns"""
    print("Generating orders...")
    
    # Get customer IDs
    customer_ids = await conn.fetch('SELECT customer_id FROM customers')
    customer_ids = [row['customer_id'] for row in customer_ids]
    
    orders = []
    batch_size = 1000
    
    # Generate orders over last 2 years
    start_date = datetime.now() - timedelta(days=730)
    
    for i in range(NUM_ORDERS):
        # Realistic date distribution (more recent orders)
        days_ago = random.randint(0, 730)
        if random.random() < 0.4:  # 40% in last 6 months
            days_ago = random.randint(0, 180)
        
        order_date = start_date + timedelta(days=days_ago)
        
        # Pick category and product
        category = random.choice(list(PRODUCTS.keys()))
        product_name, min_price, max_price = random.choice(PRODUCTS[category])
        
        # Realistic pricing (normally distributed around midpoint)
        midpoint = (min_price + max_price) / 2
        std_dev = (max_price - min_price) / 4
        price = random.gauss(midpoint, std_dev)
        price = max(min_price, min(max_price, price))  # Clamp
        
        # Status distribution (90% completed)
        status_weights = [0.90, 0.05, 0.03, 0.02]
        status = random.choices(STATUSES, weights=status_weights)[0]
        
        order = (
            random.choice(customer_ids),
            category,
            product_name,
            Decimal(str(round(price, 2))),
            order_date.date(),
            random.choice(REGIONS),
            status,
            random.choice(PAYMENT_METHODS)
        )
        orders.append(order)
        
        # Insert in batches
        if len(orders) >= batch_size:
            await conn.executemany('''
                INSERT INTO orders 
                (customer_id, product_category, product_name, order_total, 
                 order_date, region, status, payment_method)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', orders)
            print(f"  Inserted {i+1}/{NUM_ORDERS} orders...")
            orders = []
    
    # Insert remaining
    if orders:
        await conn.executemany('''
            INSERT INTO orders 
            (customer_id, product_category, product_name, order_total, 
             order_date, region, status, payment_method)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', orders)
    
    print(f"✅ Created {NUM_ORDERS} orders")

async def add_realistic_patterns(conn):
    """Add some interesting patterns for testing"""
    print("Adding realistic business patterns...")
    
    # Pattern 1: Revenue spike in November (Black Friday)
    await conn.execute('''
        INSERT INTO orders 
        (customer_id, product_category, product_name, order_total, order_date, region, status, payment_method)
        SELECT 
            (random() * 5000)::int + 1,
            'Electronics',
            'MacBook Pro',
            1800 + (random() * 700)::decimal,
            '2024-11-29'::date,
            'North America',
            'completed',
            'Credit Card'
        FROM generate_series(1, 500)
    ''')
    
    # Pattern 2: Churn spike in December (competitor launch simulation)
    await conn.execute('''
        UPDATE orders 
        SET status = 'cancelled'
        WHERE order_date >= '2024-12-01' 
          AND order_date <= '2024-12-31'
          AND product_category = 'Electronics'
          AND random() < 0.15
    ''')
    
    print("✅ Added realistic patterns")

async def create_analytics_summary(conn):
    """Create summary for verification"""
    
    # Total revenue
    total = await conn.fetchval('''
        SELECT SUM(order_total)::decimal(12,2) 
        FROM orders 
        WHERE status = 'completed'
    ''')
    
    # Orders by category
    by_category = await conn.fetch('''
        SELECT product_category, COUNT(*) as count, SUM(order_total)::decimal(12,2) as revenue
        FROM orders
        WHERE status = 'completed'
        GROUP BY product_category
        ORDER BY revenue DESC
    ''')
    
    print("\n" + "="*60)
    print("📊 DATA GENERATION SUMMARY")
    print("="*60)
    print(f"Total Revenue: ${total:,.2f}")
    print(f"\nRevenue by Category:")
    for row in by_category:
        print(f"  {row['product_category']:20s}: {row['count']:5,} orders | ${row['revenue']:10,.2f}")
    print("="*60 + "\n")

async def main():
    """Main execution"""
    
    # Load environment variables
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    print("🚀 Starting data generation...\n")
    
    # Connect to database
    conn = await asyncpg.connect(db_url)
    
    try:
        # Clear existing data
        print("Clearing existing data...")
        await conn.execute('TRUNCATE orders, customers RESTART IDENTITY CASCADE')
        
        # Generate data
        await generate_customers(conn)
        await generate_orders(conn)
        await add_realistic_patterns(conn)
        await create_analytics_summary(conn)
        
        print("✅ Data generation complete!\n")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    # Install faker first: pip install faker
    asyncio.run(main())
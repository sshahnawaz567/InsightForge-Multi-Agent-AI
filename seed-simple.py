import asyncio
import asyncpg
import random
from datetime import datetime, timedelta, date

async def seed():
    print('Connecting to database...')
    conn = await asyncpg.connect(
        'postgresql://postgres:insightforge_password@postgres-service:5432/insightforge'
    )
    
    try:
        # Check if already seeded
        count = await conn.fetchval('SELECT COUNT(*) FROM orders')
        if count > 0:
            print(f'Already seeded: {count} orders')
            return
        
        # Generate customers
        print('Creating 5000 customers...')
        customers = []
        segments = ['Enterprise', 'SMB', 'Startup']
        countries = ['USA', 'UK', 'Germany', 'France', 'India', 'Canada', 'Australia', 'Japan']
        
        for i in range(1, 5001):
            customers.append((
                # customer_id is auto-increment, don't provide it
                f'Customer {i}',  # customer_name
                f'customer{i}@example.com',  # email
                date.today() - timedelta(days=random.randint(1, 730)),  # signup_date
                random.choice(segments),  # customer_segment
                random.choice(countries)  # country
            ))
        
        await conn.executemany('''
            INSERT INTO customers (customer_name, email, signup_date, customer_segment, country)
            VALUES ($1, $2, $3, $4, $5)
        ''', customers)
        print('✅ Customers created')
        
        # Generate orders
        print('Creating 50000 orders...')
        orders = []
        categories = ['Electronics', 'Clothing', 'Home & Garden', 'Books']
        
        # Product names by category
        products = {
            'Electronics': ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Smart Watch', 'Camera'],
            'Clothing': ['T-Shirt', 'Jeans', 'Jacket', 'Shoes', 'Dress', 'Sweater'],
            'Home & Garden': ['Chair', 'Table', 'Lamp', 'Rug', 'Plant Pot', 'Curtains'],
            'Books': ['Fiction Novel', 'Business Book', 'Cookbook', 'Biography', 'Science Book', 'Self-Help']
        }
        
        regions = ['North America', 'Europe', 'Asia', 'South America', 'Australia']
        statuses = ['completed', 'pending', 'cancelled']
        payment_methods = ['Credit Card', 'PayPal', 'Bank Transfer', 'Cash on Delivery']
        
        for i in range(1, 50001):
            category = random.choice(categories)
            product_name = random.choice(products[category])
            
            orders.append((
                # order_id is auto-increment, don't provide it
                random.randint(1, 5000),  # customer_id (FK to customers)
                category,  # product_category
                product_name,  # product_name
                round(random.uniform(10, 1000), 2),  # order_total
                date.today() - timedelta(days=random.randint(1, 730)),  # order_date
                random.choice(regions),  # region
                random.choice(statuses),  # status
                random.choice(payment_methods)  # payment_method
            ))
            
            if i % 10000 == 0:
                print(f'  Progress: {i}/50000')
        
        # Batch insert
        print('Inserting orders in batches...')
        batch_size = 1000
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            await conn.executemany('''
                INSERT INTO orders (customer_id, product_category, product_name, order_total, order_date, region, status, payment_method)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', batch)
            
            if (i // batch_size + 1) % 10 == 0:
                print(f'  Inserted {i + len(batch)}/50000')
        
        # Verify
        order_count = await conn.fetchval('SELECT COUNT(*) FROM orders')
        customer_count = await conn.fetchval('SELECT COUNT(*) FROM customers')
        total_revenue = await conn.fetchval("SELECT SUM(order_total) FROM orders WHERE status='completed'")
        
        print(f'\n✅ Seeding complete!')
        print(f'   Customers: {customer_count}')
        print(f'   Orders: {order_count}')
        print(f'   Total Revenue: ${total_revenue:,.2f}')
        
        # Show sample data
        print('\n📊 Sample data:')
        sample = await conn.fetch('''
            SELECT product_category, COUNT(*) as count, SUM(order_total) as revenue
            FROM orders
            WHERE status='completed'
            GROUP BY product_category
            ORDER BY revenue DESC
        ''')
        
        for row in sample:
            print(f"   {row['product_category']}: {row['count']} orders, ${row['revenue']:,.2f}")
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        raise
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(seed())
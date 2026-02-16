-- Orders table (main table for analysis)
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    order_total DECIMAL(10,2) NOT NULL,
    order_date DATE NOT NULL,
    region VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    signup_date DATE NOT NULL,
    customer_segment VARCHAR(20), -- 'SMB', 'Enterprise', 'Individual'
    country VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_category ON orders(product_category);
CREATE INDEX idx_orders_region ON orders(region);
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Create view for common analytics
CREATE VIEW monthly_revenue AS
SELECT 
    DATE_TRUNC('month', order_date) as month,
    SUM(order_total) as revenue,
    COUNT(*) as order_count,
    AVG(order_total) as avg_order_value
FROM orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month DESC;
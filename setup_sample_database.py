#!/usr/bin/env python3
"""
Create a sample SQLite database with realistic data for testing the DB observability system.
This creates the same tables and data that match our predefined scenarios.
"""

import sqlite3
import random
from datetime import datetime, timedelta
import os

def create_sample_database(db_path="sample_ecommerce.db"):
    """Create a sample e-commerce database with realistic data."""
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🏗️  Creating sample e-commerce database...")
    
    # Create customers table
    cursor.execute("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        email TEXT UNIQUE,
        registration_date DATE
    )
    """)
    
    # Create orders table (intentionally missing indexes for demo)
    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date TIMESTAMP,
        created_at TIMESTAMP,
        total_amount DECIMAL(10,2),
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)
    
    # Insert sample customers (500K customers)
    print("👥 Inserting customers...")
    customers_data = []
    for i in range(1, 50001):  # 50K customers for faster demo
        reg_date = datetime.now() - timedelta(days=random.randint(1, 1095))  # Last 3 years
        customers_data.append((
            i,
            f"Customer_{i:06d}",
            f"customer{i}@example.com",
            reg_date.date()
        ))
    
    cursor.executemany(
        "INSERT INTO customers (customer_id, customer_name, email, registration_date) VALUES (?, ?, ?, ?)",
        customers_data
    )
    
    # Insert sample orders (1M orders)
    print("📦 Inserting orders...")
    orders_data = []
    statuses = ['completed', 'pending', 'cancelled']
    status_weights = [0.65, 0.25, 0.10]  # Match the statistics from fake_db_data
    
    for i in range(1, 100001):  # 100K orders for faster demo
        customer_id = random.randint(1, 50000)
        order_date = datetime.now() - timedelta(days=random.randint(1, 365))
        created_at = order_date + timedelta(minutes=random.randint(-30, 30))
        total_amount = round(random.uniform(10.00, 500.00), 2)
        status = random.choices(statuses, weights=status_weights)[0]
        
        orders_data.append((
            i,
            customer_id,
            order_date,
            created_at,
            total_amount,
            status
        ))
    
    cursor.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, created_at, total_amount, status) VALUES (?, ?, ?, ?, ?, ?)",
        orders_data
    )
    
    # Create some indexes (but intentionally miss the important ones for demo)
    print("🗄️  Creating some indexes...")
    cursor.execute("CREATE INDEX idx_customers_email ON customers(email)")
    # Intentionally NOT creating indexes on orders.created_at, orders.status, orders.total_amount
    # This will demonstrate the "missing index" performance issues
    
    # Add table statistics
    cursor.execute("ANALYZE")
    
    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = cursor.fetchone()[0]
    
    print(f"""
✅ Sample database created successfully!

📊 Database Stats:
   File: {os.path.abspath(db_path)}
   Size: {os.path.getsize(db_path) / 1024 / 1024:.1f} MB
   
📈 Data Summary:
   👥 Customers: {customer_count:,}
   📦 Orders: {order_count:,}
   ✅ Completed Orders: {completed_orders:,} ({completed_orders/order_count*100:.1f}%)
   
🔍 Test Queries to Try:
   
   Slow Query (missing index):
   SELECT order_id, customer_id, order_date, total_amount 
   FROM orders 
   WHERE created_at >= '2024-01-01' 
   AND status = 'completed' 
   ORDER BY total_amount DESC 
   LIMIT 100;
   
   Join Query (for testing):
   SELECT c.customer_name, COUNT(o.order_id) as order_count 
   FROM customers c 
   LEFT JOIN orders o ON c.customer_id = o.customer_id 
   WHERE c.registration_date >= '2023-01-01' 
   GROUP BY c.customer_id, c.customer_name 
   HAVING COUNT(o.order_id) > 5;

🚀 To connect in the app:
   - Use SQLite mode (I'll add this)
   - Database file: {os.path.abspath(db_path)}
""")
    
    conn.close()
    return db_path

if __name__ == "__main__":
    db_path = create_sample_database()
    print(f"\n🎯 Database ready at: {db_path}")

"""
Fake database information for testing the AI-powered DB observability system.
Contains sample queries, schemas, explain plans, logs, and other metadata.
"""

# Sample slow query scenarios
SAMPLE_DATA = {
    "slow_select_without_index": {
        "query": """
        SELECT o.order_id, o.customer_id, o.order_date, o.total_amount
        FROM orders o
        WHERE o.created_at >= '2024-01-01' 
        AND o.created_at <= '2024-12-31'
        AND o.status = 'completed'
        ORDER BY o.total_amount DESC
        LIMIT 100;
        """,
        
        "explain": """
        Sort  (cost=156423.84..156673.84 rows=100000 width=32) (actual time=2847.123..2847.156 rows=100 loops=1)
        Sort Key: total_amount DESC
        Sort Method: top-N heapsort  Memory: 32kB
        ->  Seq Scan on orders o  (cost=0.00..152423.84 rows=100000 width=32) (actual time=0.029..2823.456 rows=150000 loops=1)
                Filter: ((created_at >= '2024-01-01'::date) AND (created_at <= '2024-12-31'::date) AND ((status)::text = 'completed'::text))
                Rows Removed by Filter: 850000
        Planning Time: 0.456 ms
        Execution Time: 2847.234 ms
        """,
        
        "schema": """
        Table "public.orders"
        Column       |            Type             | Nullable |              Default
        -------------+-----------------------------+----------+-----------------------------------
        order_id     | integer                     | not null | nextval('orders_order_id_seq'::regclass)
        customer_id  | integer                     |          |
        order_date   | timestamp without time zone |          |
        created_at   | timestamp without time zone |          |
        total_amount | numeric(10,2)              |          |
        status       | character varying(50)       |          |
        
        Indexes:
            "orders_pkey" PRIMARY KEY, btree (order_id)
            
        Table size: ~1,000,000 rows
        """,
        
        "logs": """
        2024-01-15 14:23:45 UTC [12345]: LOG:  duration: 2847.234 ms  statement: SELECT o.order_id, o.customer_id...
        2024-01-15 14:23:45 UTC [12345]: LOG:  slow query detected, execution time: 2.847 seconds
        2024-01-15 14:23:45 UTC [12345]: DETAIL:  Query scanned 1000000 rows, returned 100 rows
        """,
        
        "stats": """
        Table: orders
        Estimated rows: 1000000
        Disk pages: 8547
        Average row width: 42 bytes
        Last analyze: 2024-01-10 09:15:22
        Last vacuum: 2024-01-12 02:30:15
        
        Column statistics:
        - created_at: min=2023-01-01, max=2024-12-31, null_frac=0.02
        - status: most_common_vals={completed,pending,cancelled}, frequencies={0.65,0.25,0.10}
        - total_amount: min=10.00, max=5000.00, avg=245.67
        """,
        
        "config": """
        work_mem = 4MB
        shared_buffers = 256MB
        effective_cache_size = 1GB
        random_page_cost = 4.0
        seq_page_cost = 1.0
        """,
        
        "system": """
        CPU Usage: 45%
        Memory Usage: 78%
        Disk I/O: High read activity (125 MB/s)
        Active connections: 23/100
        """
    },
    
    "inefficient_join": {
        "query": """
        SELECT c.customer_name, COUNT(o.order_id) as order_count, SUM(o.total_amount) as total_spent
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        WHERE c.registration_date >= '2023-01-01'
        GROUP BY c.customer_id, c.customer_name
        HAVING COUNT(o.order_id) > 5
        ORDER BY total_spent DESC;
        """,
        
        "explain": """
        Sort  (cost=185672.34..186172.34 rows=200000 width=64) (actual time=4523.789..4524.123 rows=45000 loops=1)
        Sort Key: (sum(o.total_amount)) DESC
        Sort Method: external merge  Disk: 12456kB
        ->  GroupAggregate  (cost=145672.34..175672.34 rows=200000 width=64) (actual time=1234.567..4456.789 loops=1)
                Group Key: c.customer_id, c.customer_name
                Filter: (count(o.order_id) > 5)
                Rows Removed by Filter: 155000
                ->  Sort  (cost=145672.34..150672.34 rows=2000000 width=32) (actual time=1234.456..2345.678 loops=1)
                      Sort Key: c.customer_id, c.customer_name
                      Sort Method: external merge  Disk: 89456kB
                      ->  Hash Left Join  (cost=25423.84..95423.84 rows=2000000 width=32) (actual time=234.567..1123.456 loops=1)
                            Hash Cond: (o.customer_id = c.customer_id)
                            ->  Seq Scan on orders o  (cost=0.00..35423.84 rows=1000000 width=16) (actual time=0.023..456.789 loops=1)
                            ->  Hash  (cost=20423.84..20423.84 rows=400000 width=24) (actual time=234.345..234.345 rows=400000 loops=1)
                                  Buckets: 65536  Batches: 8  Memory Usage: 3456kB
                                  ->  Seq Scan on customers c  (cost=0.00..20423.84 rows=400000 width=24) (actual time=0.012..123.456 loops=1)
                                        Filter: (registration_date >= '2023-01-01'::date)
                                        Rows Removed by Filter: 100000
        Planning Time: 1.234 ms
        Execution Time: 4524.456 ms
        """,
        
        "schema": """
        Table "public.customers"
        Column            |            Type             | Nullable |                Default
        ------------------+-----------------------------+----------+----------------------------------------
        customer_id       | integer                     | not null | nextval('customers_customer_id_seq'::regclass)
        customer_name     | character varying(100)      |          |
        email            | character varying(255)      |          |
        registration_date | date                        |          |
        
        Indexes:
            "customers_pkey" PRIMARY KEY, btree (customer_id)
            "customers_email_key" UNIQUE CONSTRAINT, btree (email)
            
        Table size: ~500,000 rows
        
        Foreign Key References:
        orders.customer_id -> customers.customer_id (not indexed on orders side)
        """,
        
        "logs": """
        2024-01-15 15:42:33 UTC [23456]: LOG:  duration: 4524.456 ms  statement: SELECT c.customer_name, COUNT(o.order_id)...
        2024-01-15 15:42:33 UTC [23456]: LOG:  temporary file: path "base/pgsql_tmp/pgsql_tmp23456.0", size 12456
        2024-01-15 15:42:33 UTC [23456]: LOG:  temporary file: path "base/pgsql_tmp/pgsql_tmp23456.1", size 89456
        2024-01-15 15:42:33 UTC [23456]: WARNING:  could not write to hash table, spilling to disk
        """,
        
        "stats": """
        Table: customers
        Estimated rows: 500000
        Disk pages: 4273
        Average row width: 68 bytes
        Last analyze: 2024-01-08 11:22:33
        Last vacuum: 2024-01-11 01:45:12
        
        Table: orders  
        Estimated rows: 1000000
        Most frequent customer_id values show heavy skew (top 10% customers have 60% of orders)
        """,
        
        "config": """
        work_mem = 4MB
        hash_mem_multiplier = 1.0
        enable_hashjoin = on
        enable_mergejoin = on
        enable_nestloop = on
        """,
        
        "system": """
        CPU Usage: 78%
        Memory Usage: 85%
        Disk I/O: Very high (temp files being written)
        Swap Usage: 12%
        """
    }
}

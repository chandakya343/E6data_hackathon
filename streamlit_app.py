"""
AI-Powered Database Observability - Streamlit Web Interface
Clean, minimal Swiss design for visualizing database performance analysis.
"""

import streamlit as st
import os
from datetime import datetime
from fake_db_data import SAMPLE_DATA
from gemini_client import DatabaseDiagnostician, test_connection
from xml_utils import format_diagnosis_output, clean_response_from_xml_tags
import json
import re
from collectors.sqlserver_collector import SqlServerCollector
from collectors.sqlite_collector import SqliteCollector
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any


# Swiss Design Configuration
st.set_page_config(
    page_title="SQL Observability Copilot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Swiss Design aesthetic
st.markdown("""
<style>
    /* Swiss Design Typography and Layout */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 300;
        font-size: 2.5rem;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 400;
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
        line-height: 1.5;
    }
    
    .metric-card {
        background: #ffffff;
        padding: 1.5rem;
        border: 1px solid #e0e0e0;
        border-radius: 0;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .scenario-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 500;
        font-size: 1.3rem;
        color: #1a1a1a;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .analysis-section {
        background: #fafafa;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 3px solid #333;
    }
    
    .recommendation-item {
        background: #ffffff;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #e8e8e8;
        font-family: 'Monaco', monospace;
        font-size: 0.85rem;
    }
    
    /* Minimal button styling */
    .stButton > button {
        background-color: #1a1a1a;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 400;
        border-radius: 0;
        transition: background-color 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #333;
    }
    
    /* Clean selectbox */
    .stSelectbox > div > div {
        border-radius: 0;
        border: 1px solid #ccc;
    }
    
    /* Remove default Streamlit styling */
    .streamlit-expanderHeader {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 400;
    }
    
    /* Code blocks */
    .stCodeBlock {
        font-family: 'Monaco', monospace;
        font-size: 0.85rem;
    }
    
    /* Status indicators */
    .status-success {
        color: #2e7d32;
        font-weight: 500;
    }
    
    .status-warning {
        color: #f57c00;
        font-weight: 500;
    }
    
    .status-error {
        color: #d32f2f;
        font-weight: 500;
    }
    
    /* Grid layout for metrics */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def display_header():
    """Display the main header with Swiss design."""
    st.markdown('<h1 class="main-header">SQL Observability Copilot</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-powered performance analysis and optimization recommendations</p>', unsafe_allow_html=True)
    st.info("🚀 **MVP Prototype** - Built for e6data hackathon. Fully functional SQL performance analyzer with AI-powered query improvements.")


def display_connection_status():
    """Display API connection status."""
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### System Status")
        
        with col2:
            if st.button("Test Connection", key="test_conn"):
                with st.spinner("Testing API connection..."):
                    if test_connection():
                        st.success("✅ Connected")
                    else:
                        st.error("❌ Connection Failed")


def display_scenario_selector():
    """Display scenario selection interface."""
    st.markdown("### Analysis Mode")
    
    mode = st.radio(
        "Choose analysis mode:",
        ["📋 Predefined Scenarios", "🗄️ SQLite Database", "🟠 MySQL Database", "🐘 PostgreSQL Database", "💬 AI Chat Assistant"],
        key="analysis_mode"
    )
    
    if mode == "📋 Predefined Scenarios":
        scenarios = list(SAMPLE_DATA.keys())
        scenario_names = {
            "slow_select_without_index": "Slow SELECT Query (Missing Index)",
            "inefficient_join": "Inefficient JOIN Operation"
        }
        
        selected = st.selectbox(
            "Choose a database scenario to analyze:",
            scenarios,
            format_func=lambda x: scenario_names.get(x, x),
            key="scenario_select"
        )
        
        return {"mode": "predefined", "scenario": selected}
    
    elif mode == "✏️ Custom Query":
        st.markdown("### 📝 Enter Your Database Information")
        st.info("💡 Provide as much information as possible for better analysis. Leave fields empty if not available.")
        
        custom_data = {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Query input
            custom_data["query"] = st.text_area(
                "SQL Query *",
                placeholder="SELECT * FROM users WHERE created_at > '2024-01-01'...",
                height=150,
                help="The SQL query you want to analyze"
            )
            
            # Schema input
            custom_data["schema"] = st.text_area(
                "Schema Information",
                placeholder="Table definitions, indexes, constraints...",
                height=120,
                help="Table structures, indexes, foreign keys, etc."
            )
            
            # Config input
            custom_data["config"] = st.text_area(
                "Database Configuration",
                placeholder="work_mem = 4MB\nshared_buffers = 256MB\n...",
                height=100,
                help="Relevant database configuration parameters"
            )
        
        with col2:
            # Explain plan input
            custom_data["explain"] = st.text_area(
                "Execution Plan",
                placeholder="EXPLAIN ANALYZE output...",
                height=150,
                help="Output from EXPLAIN or EXPLAIN ANALYZE"
            )
            
            # Logs input
            custom_data["logs"] = st.text_area(
                "Query Logs",
                placeholder="Slow query logs, error messages...",
                height=120,
                help="Relevant log entries, slow query logs, errors"
            )
            
            # Stats input
            custom_data["stats"] = st.text_area(
                "Table Statistics",
                placeholder="Row counts, cardinalities, histograms...",
                height=100,
                help="Table statistics, row counts, data distribution"
            )
        
        # System metrics
        custom_data["system"] = st.text_area(
            "System Metrics (Optional)",
            placeholder="CPU: 45%, Memory: 78%, Disk I/O: High...",
            height=80,
            help="System performance metrics during query execution"
        )
        
        # Validation
        if not custom_data["query"].strip():
            st.warning("⚠️ SQL Query is required for analysis")
            return {"mode": "custom", "data": None, "valid": False}
        
        return {"mode": "custom", "data": custom_data, "valid": True}

    elif mode == "🗄️ SQLite Database":
        st.markdown("### 🗄️ SQLite Database")
        st.info("💡 Perfect for testing! We've created a sample database with realistic e-commerce data.")
        
        # Dataset description
        with st.expander("📊 About the Sample Dataset", expanded=False):
            st.markdown("""
            **E-commerce Database Schema:**
            - **customers** table: 50,000 customers with name, email, registration_date
            - **orders** table: 100,000 orders with customer_id, dates, amounts, status
            
            **Built-in Performance Issues:**
            - ❌ Missing index on `orders.created_at` (date filters will be slow)
            - ❌ Missing index on `orders.status` (status filters will scan full table)
            - ❌ Missing index on `orders.total_amount` (sorting by amount will be slow)
            - ❌ No foreign key index on `orders.customer_id` (joins will be inefficient)
            
            **Data Distribution:**
            - 65% completed orders, 25% pending, 10% cancelled
            - Order amounts: $10-$500 range
            - Date range: Last 1 year of data
            - File size: ~14.4 MB
            """)
        
        # Check if sample database exists
        sample_db = "/Users/aryanchandak/projects/e6data_hackathon/sample_ecommerce.db"
        if os.path.exists(sample_db):
            if st.button("📊 Use Sample Database", key="use_sample_db"):
                st.session_state["sqlite_db_path"] = sample_db
                st.success(f"✅ Using sample database: {sample_db}")
        
        # Allow custom database path
        custom_path = st.text_input("Or enter custom SQLite database path:", 
                                  value=st.session_state.get("sqlite_db_path", sample_db))
        st.session_state["sqlite_db_path"] = custom_path
        
        # Test connection
        if st.button("Test SQLite Connection", key="test_sqlite"):
            if os.path.exists(custom_path):
                collector = SqliteCollector(custom_path)
                if collector.test_connection():
                    st.success("✅ Connected to SQLite database")
                else:
                    st.error("❌ Failed to connect to database")
            else:
                st.error("❌ Database file not found")
        
        # Query input
        st.markdown("### Query")
        
        # Query selection options - CUSTOM QUERY FEATURE
        query_option = st.radio(
            "How would you like to provide your SQL query?",
            ["📝 Write Custom Query", "📋 Use Suggested Query"],
            key="sqlite_query_option",
            horizontal=True
        )
        
        # Initialize sql_text variable
        sql_text = ""
        
        if query_option == "📋 Use Suggested Query":
            # Suggested queries section
            suggested_queries = {
                "Slow Query (Missing Index)": """SELECT order_id, customer_id, order_date, total_amount 
FROM orders 
WHERE created_at >= '2024-01-01' 
AND status = 'completed' 
ORDER BY total_amount DESC 
LIMIT 100;""",
                
                "Join Query": """SELECT c.customer_name, COUNT(o.order_id) as order_count 
FROM customers c 
LEFT JOIN orders o ON c.customer_id = o.customer_id 
WHERE c.registration_date >= '2023-01-01' 
GROUP BY c.customer_id, c.customer_name 
HAVING COUNT(o.order_id) > 5;"""
            }
            
            selected_query = st.selectbox("Choose a suggested query:", 
                                        [""] + list(suggested_queries.keys()),
                                        key="sqlite_suggested")
            
            if selected_query and selected_query in suggested_queries:
                sql_text = suggested_queries[selected_query]
                st.code(sql_text, language="sql")
            else:
                sql_text = st.text_area("SQL to analyze", 
                                      value="SELECT COUNT(*) FROM orders WHERE status = 'completed';",
                                      height=140, 
                                      key="sqlite_sql_suggested")
        else:
            # CUSTOM QUERY OPTION - This is the new feature!
            st.info("💡 **Write your own SQL query!** The sample database has `customers` and `orders` tables.")
            
            # Show schema helper
            with st.expander("📋 View Database Schema", expanded=False):
                st.markdown("""
                **📊 Available Tables:**
                
                **customers** table:
                - `customer_id` (INTEGER PRIMARY KEY)
                - `customer_name` (TEXT)
                - `email` (TEXT)  
                - `registration_date` (DATE)
                
                **orders** table:
                - `order_id` (INTEGER PRIMARY KEY)
                - `customer_id` (INTEGER)
                - `order_date` (DATE)
                - `created_at` (TIMESTAMP)
                - `total_amount` (DECIMAL)
                - `status` (TEXT) - 'completed', 'pending', 'cancelled'
                
                **💡 Query Ideas:**
                - Find high-value customers
                - Analyze order trends by date
                - Identify slow queries with complex JOINs
                - Test aggregation performance
                """)
            
            # Custom query input with example
            placeholder_query = """-- Example: Find top customers by total spending
SELECT c.customer_name, 
       COUNT(o.order_id) as order_count, 
       SUM(o.total_amount) as total_spent,
       AVG(o.total_amount) as avg_order_value
FROM customers c 
JOIN orders o ON c.customer_id = o.customer_id 
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.customer_name 
ORDER BY total_spent DESC 
LIMIT 20;"""
            
            sql_text = st.text_area(
                "✍️ Write your custom SQL query:",
                placeholder=placeholder_query,
                height=200,
                key="sqlite_sql_custom",
                help="Write any SELECT query to analyze. The system will generate an execution plan and performance recommendations."
            )
        
        estimated_only = st.checkbox("Query plan only (do not execute)", value=True, key="sqlite_plan_only")
        
        # Validation for both query types
        is_query_valid = bool(sql_text and sql_text.strip())
        
        if not is_query_valid:
            if query_option == "📋 Use Suggested Query":
                st.warning("⚠️ Please select a suggested query from the dropdown above")
            else:
                st.warning("⚠️ Please write a SQL query in the text area above")
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("🚀 Collect Diagnostics", key="sqlite_collect") and is_query_valid and custom_path:
                if os.path.exists(custom_path):
                    with st.spinner("Collecting diagnostics from SQLite database..."):
                        collector = SqliteCollector(custom_path)
                        sqlite_data = collector.collect_for_query(sql_text, estimated_plan_only=estimated_only)
                        st.session_state["sqlite_collected"] = sqlite_data
                        st.success("✅ Diagnostics collected!")
                else:
                    st.error("❌ Database file not found")
        
        with cols[1]:
            if st.button("🗑️ Clear", key="sqlite_clear"):
                st.session_state.pop("sqlite_collected", None)
                st.success("Cleared previous results")
        
        if st.session_state.get("sqlite_collected"):
            return {"mode": "sqlite", "data": st.session_state["sqlite_collected"], "valid": True}
        
        return {"mode": "sqlite", "data": None, "valid": is_query_valid}

    elif mode == "🟠 MySQL Database":
        st.markdown("### 🟠 MySQL Database")
        st.info("🚧 MySQL support coming soon! This will connect to your MySQL instances.")
        st.markdown("**Features planned:**")
        st.markdown("- EXPLAIN FORMAT=JSON support")
        st.markdown("- Performance Schema integration")
        st.markdown("- InnoDB statistics collection")
        st.markdown("- Query optimization suggestions")
        return {"mode": "mysql", "data": None, "valid": False}

    elif mode == "🐘 PostgreSQL Database":
        st.markdown("### 🐘 PostgreSQL Database")
        st.info("🚧 PostgreSQL support coming soon! This will connect to your PostgreSQL instances.")
        st.markdown("**Features planned:**")
        st.markdown("- EXPLAIN (ANALYZE, BUFFERS) support")
        st.markdown("- pg_stat_* table analysis")
        st.markdown("- Index usage statistics")
        st.markdown("- Query performance insights")
        return {"mode": "postgresql", "data": None, "valid": False}

    elif mode == "💬 AI Chat Assistant":
        st.markdown("### 💬 AI Chat Assistant")
        st.info("💡 Chat with our SQL performance expert! Ask questions about your queries, get optimization tips, or discuss database performance.")
        
        # Initialize chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "👋 Hi! I'm your SQL performance assistant. How can I help you optimize your database queries today?"}
            ]
        
        # Display chat history
        with st.container():
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about SQL performance, query optimization, or database issues..."):
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            try:
                diagnostician = DatabaseDiagnostician()
                
                # Build simplified history of user/response pairs (exclude the latest user input)
                pairs = []
                pending_user = None
                for m in st.session_state.chat_history[:-1]:
                    if m["role"] == "user":
                        pending_user = m["content"]
                    elif m["role"] == "assistant" and pending_user is not None:
                        pairs.append({"user": pending_user, "response": m["content"]})
                        pending_user = None

                # Get assistant response using simplified protocol
                reply = diagnostician.chat_respond(history=pairs, user_message=prompt)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I encountered an error: {str(e)}"})
            
            st.rerun()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = [
                {"role": "assistant", "content": "👋 Hi! I'm your SQL performance assistant. How can I help you optimize your database queries today?"}
            ]
            st.rerun()
        
        return {"mode": "chat", "data": None, "valid": False}

    else:
        st.markdown("### 🟦 Live SQL Server Connection")
        st.info("Provide connection details. Password will not be displayed.")
        if "sqlserver" not in st.session_state:
            st.session_state["sqlserver"] = {
                "server": "localhost,1433",
                "database": "master",
                "username": "sa",
                "password": "",
                "driver": "ODBC Driver 18 for SQL Server",
                "encrypt": True,
                "trust": True,
            }
        conn = st.session_state["sqlserver"]
        col1, col2 = st.columns(2)
        with col1:
            conn["server"] = st.text_input("Server,Port", value=conn["server"])    
            conn["database"] = st.text_input("Database", value=conn["database"])    
            conn["username"] = st.text_input("Username", value=conn["username"])    
        with col2:
            conn["password"] = st.text_input("Password", value=conn["password"], type="password")
            conn["driver"] = st.text_input("ODBC Driver", value=conn["driver"])    
            conn["encrypt"] = st.checkbox("Encrypt", value=conn["encrypt"])    
            conn["trust"] = st.checkbox("Trust Server Certificate", value=conn["trust"])    

        st.markdown("### Query")
        sql_text = st.text_area("SQL to analyze", height=140, placeholder="SELECT TOP 100 * FROM sys.objects ORDER BY create_date DESC;")
        estimated_only = st.checkbox("Estimated plan only (do not execute)", value=True)
        cols = st.columns(3)
        live_state = {"valid": bool(sql_text.strip()), "data": None}
        with cols[0]:
            if st.button("Test Connection", key="live_test_conn"):
                collector = SqlServerCollector(
                    server=conn["server"],
                    database=conn["database"],
                    username=conn["username"],
                    password=conn["password"],
                    driver=conn["driver"],
                    encrypt=conn["encrypt"],
                    trust_server_cert=conn["trust"],
                )
                ok = collector.test_connection()
                if ok:
                    st.success("Connected to SQL Server")
                else:
                    st.error("Connection failed")
        with cols[1]:
            if st.button("Collect Diagnostics", key="live_collect") and sql_text.strip():
                with st.spinner("Collecting diagnostics from SQL Server..."):
                    collector = SqlServerCollector(
                        server=conn["server"],
                        database=conn["database"],
                        username=conn["username"],
                        password=conn["password"],
                        driver=conn["driver"],
                        encrypt=conn["encrypt"],
                        trust_server_cert=conn["trust"],
                    )
                    live = collector.collect_for_query(sql_text, estimated_plan_only=estimated_only)
                    st.session_state["live_collected"] = live
        with cols[2]:
            if st.button("Clear", key="live_clear"):
                st.session_state.pop("live_collected", None)

        if st.session_state.get("live_collected"):
            st.success("Diagnostics collected. You can now Analyze or Improve & Compare.")
            return {"mode": "live", "data": st.session_state["live_collected"], "valid": True}

        if not sql_text.strip():
            st.warning("Enter a SQL query to proceed")
        return {"mode": "live", "data": None, "valid": False}


def display_query_preview(scenario_key):
    """Display the query and basic info for the selected scenario."""
    data = SAMPLE_DATA[scenario_key]
    
    st.markdown("### Query Preview")
    
    # Query
    with st.expander("📝 SQL Query", expanded=True):
        st.code(data["query"].strip(), language="sql")
    
    # Execution plan preview
    with st.expander("📊 Execution Plan", expanded=False):
        st.code(data["explain"].strip(), language="text")
    
    # Schema info
    with st.expander("🗄️ Schema Information", expanded=False):
        st.code(data["schema"].strip(), language="text")


def display_analysis_results(diagnosis):
    """Display the AI analysis results with Swiss design."""
    if not diagnosis:
        return
    
    # Reasoning section
    st.markdown("### 🔍 Analysis")
    reasoning = diagnosis.get("reasoning", "No analysis available")
    st.markdown(f'<div class="analysis-section">{reasoning}</div>', unsafe_allow_html=True)
    
    # Metrics overview
    bottlenecks = diagnosis.get("bottlenecks", [])
    root_causes = diagnosis.get("root_causes", [])
    recommendations = diagnosis.get("recommendations", [])
    comments = diagnosis.get("comments", [])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Bottlenecks", len(bottlenecks))
    
    with col2:
        st.metric("Issues Found", len(root_causes))
    
    with col3:
        st.metric("Recommendations", len(recommendations))
    
    with col4:
        st.metric("Additional Tips", len(comments))
    
    # Bottlenecks section
    if bottlenecks:
        st.markdown("### 🚨 Performance Bottlenecks")
        for i, bottleneck in enumerate(bottlenecks, 1):
            severity = bottleneck.get('severity', 'Medium')
            severity_color = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(severity, "🟠")
            with st.container():
                st.markdown(f"**{i}. {severity_color} {bottleneck.get('type', 'Unknown')} ({severity} Severity)**")
                st.markdown(f"_{bottleneck.get('description', 'No description')}_")
                st.markdown("---")
    
    # Root causes
    if root_causes:
        st.markdown("### ⚠️ Root Causes")
        for i, cause in enumerate(root_causes, 1):
            with st.container():
                st.markdown(f"**{i}. {cause.get('type', 'Unknown')}**")
                st.markdown(f"_{cause.get('description', 'No description')}_")
                st.markdown("---")
    
    # Recommendations
    if recommendations:
        st.markdown("### 💡 Recommendations")
        for i, rec in enumerate(recommendations, 1):
            with st.container():
                st.markdown(f"**{i}. {rec.get('type', 'Unknown')}**")
                
                # Check if it's SQL code and format appropriately
                description = rec.get('description', 'No description')
                if 'CREATE INDEX' in description or 'SELECT' in description or 'ANALYZE' in description:
                    st.code(description, language="sql")
                else:
                    st.markdown(description)
                st.markdown("---")
    
    # Additional comments
    if comments:
        st.markdown("### 📝 Additional Insights")
        for comment in comments:
            st.info(f"💡 {comment}")


def _extract_elapsed_ms_from_logs(log_text: str):
    """Extract elapsed ms from collector logs."""
    try:
        patterns = [
            r"Execution elapsed:\s*([0-9.]+)\s*ms",
            r"elapsed:?\s*([0-9.]+)\s*ms",
            r"([0-9.]+)\s*ms\s*elapsed",
        ]
        text = log_text or ""
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return float(m.group(1))
    except Exception:
        pass
    return None


def initialize_improvement_tracking():
    """Initialize session state for tracking improvement iterations."""
    if "improvement_history" not in st.session_state:
        st.session_state.improvement_history = []
    if "current_iteration" not in st.session_state:
        st.session_state.current_iteration = 0
    if "base_query_data" not in st.session_state:
        st.session_state.base_query_data = None
    if "baseline_selection" not in st.session_state:
        st.session_state.baseline_selection = "Original"
    if "improved_versions" not in st.session_state:
        st.session_state.improved_versions = []


def add_iteration_to_history(query: str, execution_time_ms: float, diagnosis: dict, iteration_type: str = "improved"):
    """Add a query iteration to the improvement history."""
    iteration_data = {
        "iteration": st.session_state.current_iteration,
        "query": query,
        "execution_time_ms": execution_time_ms,
        "diagnosis": diagnosis,
        "timestamp": datetime.now().isoformat(),
        "type": iteration_type  # "original", "improved", "recursive"
    }
    st.session_state.improvement_history.append(iteration_data)
    # Maintain improved_versions cache for quick UI access
    try:
        if "improved_versions" in st.session_state:
            st.session_state.improved_versions.append({
                "iteration": iteration_data["iteration"],
                "type": iteration_type,
                "execution_time_ms": execution_time_ms,
                "query": query,
                "diagnosis": diagnosis,
            })
    except Exception:
        pass
    st.session_state.current_iteration += 1


def plot_improvement_progress():
    """Create a plotly chart showing SQL improvement progress over iterations."""
    if not st.session_state.get("improvement_history") or len(st.session_state.improvement_history) < 2:
        st.info("📊 Run at least 2 iterations to see improvement progress")
        return
    
    history = st.session_state.improvement_history
    
    # Extract data for plotting
    iterations = [item["iteration"] for item in history]
    execution_times = [item["execution_time_ms"] for item in history if item["execution_time_ms"] is not None]
    iteration_labels = [item["iteration"] for item in history if item["execution_time_ms"] is not None]
    types = [item["type"] for item in history if item["execution_time_ms"] is not None]
    
    if len(execution_times) < 2:
        st.info("📊 Need execution time data from at least 2 iterations to show progress")
        return
    
    # Create the plot
    fig = go.Figure()
    
    # Add line chart
    fig.add_trace(go.Scatter(
        x=iteration_labels,
        y=execution_times,
        mode='lines+markers',
        name='Execution Time',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8, color='#1f77b4')
    ))
    
    # Add markers for different types
    colors = {"original": "red", "improved": "orange", "recursive": "green"}
    for i, (time, label, type_) in enumerate(zip(execution_times, iteration_labels, types)):
        fig.add_trace(go.Scatter(
            x=[label],
            y=[time],
            mode='markers',
            name=type_.title(),
            marker=dict(size=12, color=colors.get(type_, "blue")),
            showlegend=(i == 0 or type_ not in [t["type"] for t in history[:i]])
        ))
    
    # Add original baseline line if available
    original_items = [item for item in history if item.get("type") == "original" and item.get("execution_time_ms") is not None]
    if original_items:
        baseline = original_items[0]["execution_time_ms"]
        if execution_times:
            fig.add_trace(go.Scatter(
                x=iteration_labels,
                y=[baseline] * len(iteration_labels),
                mode='lines',
                name='Original Baseline',
                line=dict(color='#d62728', width=2, dash='dash')
            ))

    # Calculate improvement percentage
    if len(execution_times) >= 2:
        initial_time = execution_times[0]
        final_time = execution_times[-1]
        improvement_pct = ((initial_time - final_time) / initial_time) * 100
        
        # Add improvement annotation
        fig.add_annotation(
            x=iteration_labels[-1],
            y=execution_times[-1],
            text=f"Total Improvement: {improvement_pct:.1f}%",
            showarrow=True,
            arrowhead=2,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#333",
            borderwidth=1
        )
    
    # Update layout with Swiss design aesthetics
    fig.update_layout(
        title={
            'text': "SQL Query Performance Enhancement Progress",
            'x': 0.5,
            'font': {'family': 'Helvetica Neue', 'size': 20, 'color': '#1a1a1a'}
        },
        xaxis_title="Iteration",
        yaxis_title="Execution Time (ms)",
        font=dict(family="Helvetica Neue", size=12, color="#333"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e0e0e0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e0e0e0')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Iterations", len(history))
    with col2:
        if len(execution_times) >= 2:
            st.metric("Time Improvement", f"{improvement_pct:.1f}%", 
                     delta=f"{initial_time - final_time:.1f}ms")
    with col3:
        st.metric("Best Time", f"{min(execution_times):.1f}ms")


def _get_improvement_versions():
    """Return labeled versions from history including original and improvements."""
    versions = []
    improved_counter = 0
    for item in st.session_state.improvement_history:
        label = ""
        if item.get("type") == "original":
            label = "Original"
        else:
            improved_counter += 1
            if item.get("type") == "recursive":
                label = f"Improved {improved_counter} (Recursive)"
            else:
                label = f"Improved {improved_counter}"
        versions.append({
            "label": label,
            "iteration": item.get("iteration"),
            "type": item.get("type"),
            "execution_time_ms": item.get("execution_time_ms"),
            "query": item.get("query"),
            "diagnosis": item.get("diagnosis"),
        })
    return versions


def _format_chat_analysis_xml(xml_content: str) -> str:
    """Parse and format XML analysis content for chat display."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_content)
        
        markdown_parts = []
        
        # Summary
        summary_elem = root.find("summary")
        if summary_elem is not None and summary_elem.text:
            markdown_parts.append(summary_elem.text.strip())
            markdown_parts.append("")  # Empty line
        
        # Bottlenecks
        bottlenecks_elem = root.find("bottlenecks")
        if bottlenecks_elem is not None:
            bottlenecks = bottlenecks_elem.findall("bottleneck")
            if bottlenecks:
                markdown_parts.append("### 🚨 **Performance Bottlenecks**")
                for bottleneck in bottlenecks:
                    b_type = bottleneck.get("type", "Unknown")
                    severity = bottleneck.get("severity", "Medium")
                    description = bottleneck.text.strip() if bottleneck.text else ""
                    severity_icon = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(severity, "🟠")
                    markdown_parts.append(f"- {severity_icon} **{b_type}** ({severity}): {description}")
                markdown_parts.append("")
        
        # Recommendations
        recommendations_elem = root.find("recommendations")
        if recommendations_elem is not None:
            recommendations = recommendations_elem.findall("recommendation")
            if recommendations:
                markdown_parts.append("### 💡 **Recommendations**")
                for rec in recommendations:
                    r_type = rec.get("type", "Unknown")
                    priority = rec.get("priority", "Medium")
                    description = rec.text.strip() if rec.text else ""
                    priority_icon = {"High": "🔥", "Medium": "⚡", "Low": "💡"}.get(priority, "⚡")
                    markdown_parts.append(f"- {priority_icon} **{r_type}** ({priority}): {description}")
                markdown_parts.append("")
        
        # Tips
        tips_elem = root.find("tips")
        if tips_elem is not None:
            tips = tips_elem.findall("tip")
            if tips:
                markdown_parts.append("### 🎯 **Pro Tips**")
                for tip in tips:
                    tip_text = tip.text.strip() if tip.text else ""
                    markdown_parts.append(f"- 💡 {tip_text}")
        
        return "\n".join(markdown_parts)
        
    except Exception as e:
        # Fallback to original content if XML parsing fails
        return f"Analysis response (XML parsing failed): {xml_content}"


def _process_chat_response(raw_response: str, conversation_started: bool) -> str:
    """Process chat response based on conversation state and format."""
    try:
        if not conversation_started:
            # First interaction - check for XML analysis format
            if "<analysis>" in raw_response and "</analysis>" in raw_response:
                # Extract and format XML content
                start_idx = raw_response.find("<analysis>")
                end_idx = raw_response.find("</analysis>") + len("</analysis>")
                xml_content = raw_response[start_idx:end_idx]
                
                # Parse XML content and return formatted response
                return _format_chat_analysis_xml(xml_content)
            else:
                # Regular response for first interaction - clean any XML tags
                return clean_response_from_xml_tags(raw_response)
        else:
            # Subsequent interactions - look for simple response tags
            if "<response>" in raw_response and "</response>" in raw_response:
                # Extract content between response tags
                start_idx = raw_response.find("<response>") + len("<response>")
                end_idx = raw_response.find("</response>")
                response_content = raw_response[start_idx:end_idx].strip()
                # Clean any remaining XML tags from the content
                return clean_response_from_xml_tags(response_content)
            else:
                # Fallback to cleaned raw response if no tags found
                return clean_response_from_xml_tags(raw_response)
                
    except Exception as e:
        # Fallback to cleaned raw response on any error
        return clean_response_from_xml_tags(raw_response)

def run_analysis(data_source):
    """Run the AI analysis for the selected scenario or custom data."""
    try:
        # Initialize diagnostician
        diagnostician = DatabaseDiagnostician()
        
        # Get data based on source type
        if isinstance(data_source, str):
            # Predefined scenario
            db_data = SAMPLE_DATA[data_source]
        else:
            # Custom data
            db_data = data_source
        
        # Run analysis
        with st.spinner("🤖 Analyzing database performance..."):
            diagnosis = diagnostician.analyze_performance(db_data)
        
        return diagnosis
    
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None


def handle_query_comparison():
    """Handle the execution and comparison of original vs improved queries."""
    db_path = st.session_state.get("sqlite_db_path")
    improved = st.session_state.get('improved_sql')
    base_data = st.session_state.get('base_query_data')
    
    if not db_path or not improved or not base_data:
        st.error("Missing required data for comparison")
        return
    
    collector = SqliteCollector(db_path)
    
    # Run original query
    with st.spinner("Running original query..."):
        original_query = base_data.get("query", "")
        base_exec = collector.collect_for_query(original_query, estimated_plan_only=False)
    
    # Run improved query (only if valid SELECT)
    with st.spinner("Running improved query..."):
        improved_query = improved.get("improved_query", "")
        if not improved_query or not improved_query.strip().lower().startswith("select"):
            st.warning("Improved query is not a valid SELECT. Skipping execution.")
            improved_exec = {"logs": "", "result_preview": ""}
        else:
            improved_exec = collector.collect_for_query(improved_query, estimated_plan_only=False)
    
    # Extract execution times
    base_ms = _extract_elapsed_ms_from_logs(base_exec.get("logs", ""))
    imp_ms = _extract_elapsed_ms_from_logs(improved_exec.get("logs", ""))
    
    # Add improved query to history (only if executed and timed)
    if imp_ms is not None:
        # Analyze the improved query
        diagnostician = DatabaseDiagnostician()
        improved_diagnosis = diagnostician.analyze_performance(improved_exec)
        
        add_iteration_to_history(
            query=improved_query,
            execution_time_ms=imp_ms,
            diagnosis=improved_diagnosis,
            iteration_type="improved"
        )
    
    # Display comparison results
    st.markdown("### 🔄 Execution Comparison")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Original Time (ms)", base_ms if base_ms is not None else "n/a")
    with col2:
        st.metric("Improved Time (ms)", imp_ms if imp_ms is not None else "n/a")
    with col3:
        if base_ms is not None and imp_ms is not None:
            improvement = ((base_ms - imp_ms) / base_ms) * 100
            st.metric("Improvement %", f"{improvement:.1f}%", delta=f"{base_ms - imp_ms:.1f}ms")
    
    # Result previews
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Original Query Results"):
            if base_exec.get("result_preview"):
                st.code(base_exec.get("result_preview"), language="text")
            else:
                st.text("(no preview)")
    
    with col2:
        with st.expander("Improved Query Results"):
            if improved_exec.get("result_preview"):
                st.code(improved_exec.get("result_preview"), language="text")
            else:
                st.text("(no preview)")
    
    # Performance feedback
    if base_ms is not None and imp_ms is not None:
        if imp_ms < base_ms:
            st.success(f"🎉 Improved query is faster by {round(base_ms - imp_ms, 2)} ms ({improvement:.1f}% improvement)")
        elif imp_ms == base_ms:
            st.info("⚖️ Both queries perform similarly")
        else:
            st.warning(f"⚠️ Improved query is slower by {round(imp_ms - base_ms, 2)} ms")
    elif base_ms is not None and imp_ms is None:
        st.info("Improved query was not executed (invalid or non-SELECT). Only original timing is available.")


def handle_recursive_improvement():
    """Handle recursive improvement by using the latest query iteration."""
    if not st.session_state.improvement_history:
        st.error("No previous iterations found for recursive improvement")
        return
    
    # Get the latest iteration
    latest_iteration = st.session_state.improvement_history[-1]
    base_data = st.session_state.get('base_query_data')
    
    if not base_data:
        st.error("Base query data not found")
        return
    
    # Create enhanced data using latest query + all original diagnostics
    enhanced_data = dict(base_data)  # Copy original data
    enhanced_data["query"] = latest_iteration["query"]  # Use latest improved query
    
    # Add comprehensive context from all iterations
    iteration_context = "\n".join([
        f"Iteration {i['iteration']} ({i['type']}): {i['execution_time_ms']}ms - {i['query'][:100]}..."
        for i in st.session_state.improvement_history
    ])
    
    enhanced_data["improvement_history"] = iteration_context
    
    # Generate recursive improvement
    diagnostician = DatabaseDiagnostician()
    
    with st.spinner("Generating recursively improved query..."):
        # Use latest diagnosis and all historical context
        latest_diagnosis = latest_iteration["diagnosis"]
        improved = diagnostician.improve_query(
            enhanced_data,
            prior_diagnosis_xml=latest_diagnosis.get('raw_response'),
            prior_diagnosis=latest_diagnosis
        )
    
    st.session_state['improved_sql'] = improved
    st.success(f"🔄 Generated recursively improved query (iteration {st.session_state.current_iteration + 1})")
    
    # Automatically run and compare the new query
    if improved.get("improved_query") and improved.get("improved_query").strip().lower().startswith("select"):
        db_path = st.session_state.get("sqlite_db_path")
        if db_path:
            collector = SqliteCollector(db_path)
            
            with st.spinner("Testing recursively improved query..."):
                recursive_exec = collector.collect_for_query(improved.get("improved_query"), estimated_plan_only=False)
            
            recursive_ms = _extract_elapsed_ms_from_logs(recursive_exec.get("logs", ""))
            
            if recursive_ms is not None:
                # Analyze the recursive query
                recursive_diagnosis = diagnostician.analyze_performance(recursive_exec)
                
                add_iteration_to_history(
                    query=improved.get("improved_query"),
                    execution_time_ms=recursive_ms,
                    diagnosis=recursive_diagnosis,
                    iteration_type="recursive"
                )
                
                # Show immediate feedback
                previous_time = latest_iteration["execution_time_ms"]
                if recursive_ms < previous_time:
                    improvement = ((previous_time - recursive_ms) / previous_time) * 100
                    st.success(f"🚀 Recursive improvement successful! {improvement:.1f}% faster than previous iteration")
                else:
                    st.info("🔄 Recursive iteration complete. Check the progress chart for overall trends.")


def main():
    """Main Streamlit application."""
    display_header()
    
    # Check if API key is configured
    if not os.getenv("GEMINI_API_KEY"):
        st.error("⚠️ GEMINI_API_KEY environment variable not set. Please configure your API key.")
        st.info("Create a .env file with: GEMINI_API_KEY=your_api_key_here")
        return
    
    st.markdown("---")
    
    # Scenario/Mode selection
    selection = display_scenario_selector()
    
    if selection["mode"] == "predefined" and selection["scenario"]:
        # Predefined scenario flow
        selected_scenario = selection["scenario"]
        
        # Query preview
        display_query_preview(selected_scenario)
        
        st.markdown("---")
        
        # Analysis button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Analyze Performance", key="analyze_btn", use_container_width=True):
                diagnosis = run_analysis(selected_scenario)
                
                if diagnosis:
                    st.session_state['current_diagnosis'] = diagnosis
                    st.session_state['current_scenario'] = selected_scenario
                    st.session_state['current_mode'] = "predefined"
        
        # Display results if available
        if ('current_diagnosis' in st.session_state and 
            st.session_state.get('current_scenario') == selected_scenario and
            st.session_state.get('current_mode') == "predefined"):
            st.markdown("---")
            st.markdown("## 📊 Analysis Results")
            display_analysis_results(st.session_state['current_diagnosis'])
    
    elif selection["mode"] == "sqlite":
        # Initialize improvement tracking
        initialize_improvement_tracking()
        
        sqlite_data = selection.get("data")
        if selection.get("valid") and sqlite_data:
            st.markdown("### Preview")
            with st.expander("📝 SQL Query", expanded=True):
                st.code(sqlite_data.get("query", "").strip(), language="sql")
            with st.expander("📊 Query Plan"):
                st.text(sqlite_data.get("explain", "(no plan)"))
            if sqlite_data.get("result_preview"):
                with st.expander("📄 Result Preview"):
                    st.code(sqlite_data.get("result_preview"), language="text")
            with st.expander("🗄️ Schema"):
                st.text(sqlite_data.get("schema", "(no schema)"))
            with st.expander("📈 Stats"):
                st.text(sqlite_data.get("stats", "(no stats)"))
            with st.expander("📝 Logs"):
                log_text = sqlite_data.get("logs", "(no logs)")
                st.code(log_text, language="text")
                st.download_button("Download Logs", log_text, file_name="sqlite_logs.txt")

            st.markdown("---")
            
            # Step 1: Collect Diagnostics
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button("🚀 Collect Diagnostics", key="sqlite_collect_step", use_container_width=True):
                    # Store base query data for future iterations
                    st.session_state.base_query_data = sqlite_data
                    st.session_state['diagnostics_collected'] = True
                    st.success("✅ Diagnostics collected! You can now analyze performance.")
            
            # Step 2: Analyze Performance (only show if diagnostics collected)
            if st.session_state.get('diagnostics_collected'):
                st.markdown("---")
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    if st.button("🔍 Analyze Performance", key="sqlite_analyze", use_container_width=True):
                        diagnosis = run_analysis(sqlite_data)
                        if diagnosis:
                            st.session_state['current_diagnosis'] = diagnosis
                            st.session_state['current_mode'] = "sqlite"
                            
                            # Add original query to improvement history
                            original_time = _extract_elapsed_ms_from_logs(sqlite_data.get("logs", ""))
                            if original_time is not None:
                                add_iteration_to_history(
                                    query=sqlite_data.get("query", ""),
                                    execution_time_ms=original_time,
                                    diagnosis=diagnosis,
                                    iteration_type="original"
                                )

            # Step 3: Display Analysis Results (only show if we have analysis)
            if 'current_diagnosis' in st.session_state and st.session_state.get('current_mode') == "sqlite":
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")
                display_analysis_results(st.session_state['current_diagnosis'])

                # Step 4: Improvement Options (placed AFTER analysis results)
                st.markdown("---")
                st.markdown("## 🚀 Query Improvement Options")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✨ Generate Improved Query", key="sqlite_improve", use_container_width=True):
                        diagnostician = DatabaseDiagnostician()
                        
                        # Get the most recent query and diagnosis for recursive improvement
                        current_data = st.session_state.base_query_data
                        if st.session_state.improvement_history:
                            # Use the latest iteration for recursive improvement
                            latest_iteration = st.session_state.improvement_history[-1]
                            current_data = dict(current_data)  # Copy base data
                            current_data["query"] = latest_iteration["query"]  # Use latest query
                        
                        prior_diag = st.session_state.get('current_diagnosis')
                        prior_xml = prior_diag.get('raw_response') if isinstance(prior_diag, dict) else None
                        
                        improved = diagnostician.improve_query(
                            current_data, 
                            prior_diagnosis_xml=prior_xml, 
                            prior_diagnosis=prior_diag if isinstance(prior_diag, dict) else None
                        )
                        # Guard: ensure improved SELECT is present
                        if improved.get("improved_query"):
                            st.session_state['improved_sql'] = improved
                            st.success("✅ Improved query generated!")
                        else:
                            st.warning("The model did not return a valid SELECT statement. Try again or adjust inputs.")
                
                with col2:
                    if st.session_state.get('improved_sql'):
                        if st.button("🔄 Run & Compare All Queries", key="sqlite_compare_exec", use_container_width=True):
                            handle_query_comparison()
                
                # Display improvement progress chart
                if st.session_state.improvement_history:
                    st.markdown("### 📈 Improvement Progress")
                    plot_improvement_progress()
                
                # Display improved query if available
                if st.session_state.get('improved_sql'):
                    st.markdown("### 🔧 Improved Query Versions")
                    versions = _get_improvement_versions()

                    # Sidebar: version picker and actions
                    with st.sidebar:
                        st.markdown("### 🧪 Compare & Select Version")
                        labels = [v["label"] for v in versions]
                        if labels:
                            idx = st.selectbox("Choose version to inspect", list(range(len(labels))), format_func=lambda i: labels[i])
                            selected = versions[idx]
                            st.metric("Runtime (ms)", selected.get("execution_time_ms", "n/a"))
                            if st.button("Use this as baseline for next improvement"):
                                # Set as baseline for next improvement iteration
                                st.session_state.base_query_data = dict(st.session_state.base_query_data or {})
                                if st.session_state.base_query_data is not None:
                                    st.session_state.base_query_data["query"] = selected["query"]
                                st.session_state.baseline_selection = selected["label"]
                                st.success(f"Baseline set to {selected['label']}")
                        
                        if versions:
                            # Find best time
                            valid = [v for v in versions if v.get("execution_time_ms") is not None]
                            if valid:
                                best = min(valid, key=lambda v: v["execution_time_ms"]) 
                                if st.button("✅ Use Best Query"):
                                    st.session_state.base_query_data = dict(st.session_state.base_query_data or {})
                                    st.session_state.base_query_data["query"] = best["query"]
                                    st.success(f"Best query selected: {best['label']} ({best['execution_time_ms']:.2f} ms)")

                    # Main area: dropdown to select and view any SQL version
                    versions = _get_improvement_versions()
                    if versions:
                        # Add session state for selected version if not exists
                        if "selected_version_idx" not in st.session_state:
                            st.session_state.selected_version_idx = len(versions) - 1  # Default to latest
                        
                        # Dropdown to select version
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            labels = [f"{v['label']} ({v.get('execution_time_ms', 'n/a')} ms)" for v in versions]
                            selected_idx = st.selectbox(
                                "Select SQL Version to View:",
                                options=list(range(len(labels))),
                                format_func=lambda i: labels[i],
                                index=st.session_state.selected_version_idx,
                                key="version_dropdown"
                            )
                            st.session_state.selected_version_idx = selected_idx
                        
                        selected_version = versions[selected_idx]
                        runtime = selected_version.get("execution_time_ms")
                        
                        with col2:
                            # Show runtime metric for selected version
                            if runtime is not None:
                                st.metric("Runtime", f"{runtime:.2f} ms")
                        
                        with col3:
                            # Show improvement vs original
                            if len(versions) > 1 and runtime is not None:
                                original_time = next((v.get("execution_time_ms") for v in versions if v.get("type") == "original"), None)
                                if original_time is not None and original_time != runtime:
                                    improvement = ((original_time - runtime) / original_time) * 100
                                    st.metric("vs Original", f"{improvement:+.1f}%")
                        
                        with col4:
                            # Use selected version as baseline button
                            if st.button("🎯 Use as Baseline", key="use_selected_baseline", help="Use this query as the starting point for the next improvement"):
                                st.session_state.base_query_data = dict(st.session_state.base_query_data or {})
                                if st.session_state.base_query_data is not None:
                                    st.session_state.base_query_data["query"] = selected_version["query"]
                                st.session_state.baseline_selection = selected_version["label"]
                                st.success(f"✅ Baseline set to {selected_version['label']}")
                        
                        # Display selected query
                        with st.expander(f"📝 SQL Query: {selected_version['label']}", expanded=True):
                            st.code(selected_version.get("query", ""), language="sql")
                            
                            # Show rationale if this is an improved version and we have it
                            if (selected_version.get("type") in ["improved", "recursive"] and 
                                selected_idx == len(versions) - 1 and  # Latest version
                                st.session_state.get('improved_sql', {}).get("rationale")):
                                st.info(f"**Rationale:** {st.session_state['improved_sql']['rationale']}")
                    
                    # Option for recursive improvement
                    if st.button("🔄 Generate Even Better Query (Recursive)", key="sqlite_recursive"):
                        handle_recursive_improvement()
    
    elif selection["mode"] == "mysql" or selection["mode"] == "postgresql":
        # These modes are placeholders - no functionality yet
        st.info("🚧 This database type is coming soon! For now, try the SQLite Database mode.")
    
    elif selection["mode"] == "chat":
        # Chat mode is handled in display_scenario_selector
        pass
    
    # Clear improvement history button (for debugging/reset)
    if st.session_state.get("improvement_history"):
        with st.sidebar:
            st.markdown("### 🔧 Development Tools")
            if st.button("🗑️ Clear Improvement History"):
                st.session_state.improvement_history = []
                st.session_state.current_iteration = 0
                st.session_state.pop('improved_sql', None)
                st.session_state.pop('current_diagnosis', None)
                st.success("Improvement history cleared")
                st.rerun()



if __name__ == "__main__":
    main()

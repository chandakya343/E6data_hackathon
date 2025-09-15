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
            default_sql = suggested_queries[selected_query]
        else:
            default_sql = "SELECT COUNT(*) FROM orders WHERE status = 'completed';"
            
        sql_text = st.text_area("SQL to analyze", 
                              value=default_sql if selected_query else "",
                              height=140, 
                              key="sqlite_sql")
        
        estimated_only = st.checkbox("Query plan only (do not execute)", value=True, key="sqlite_plan_only")
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("Collect Diagnostics", key="sqlite_collect") and sql_text.strip() and custom_path:
                if os.path.exists(custom_path):
                    with st.spinner("Collecting diagnostics from SQLite database..."):
                        collector = SqliteCollector(custom_path)
                        sqlite_data = collector.collect_for_query(sql_text, estimated_plan_only=estimated_only)
                        st.session_state["sqlite_collected"] = sqlite_data
                        st.success("✅ Diagnostics collected!")
                else:
                    st.error("Database file not found")
        
        with cols[1]:
            if st.button("Clear", key="sqlite_clear"):
                st.session_state.pop("sqlite_collected", None)
        
        if st.session_state.get("sqlite_collected"):
            return {"mode": "sqlite", "data": st.session_state["sqlite_collected"], "valid": True}
        
        if not sql_text.strip():
            st.warning("Enter a SQL query to proceed")
        return {"mode": "sqlite", "data": None, "valid": False}

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
        
        # Initialize chat history and conversation state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "👋 Hi! I'm your SQL performance assistant. How can I help you optimize your database queries today?"}
            ]
        
        if "conversation_started" not in st.session_state:
            st.session_state.conversation_started = False
        
        # Chat container
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
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
            
            # Generate AI response
            try:
                diagnostician = DatabaseDiagnostician()
                
                # Check if this is the first substantial interaction
                if not st.session_state.conversation_started:
                    # First interaction - use XML format for analysis
                    analysis_keywords = ["analyze", "performance", "bottleneck", "optimize", "slow", "improve", "diagnose", "explain plan", "query", "sql"]
                    is_analysis_request = any(keyword in prompt.lower() for keyword in analysis_keywords)
                    
                    if is_analysis_request:
                        # Enhanced prompt for analysis with XML output (first interaction only)
                        chat_prompt = f"""You are a SQL performance expert. The user asked: "{prompt}"

This is the first substantial interaction, so provide a structured analysis in this XML format:

<analysis>
  <summary>Brief conversational response to their question</summary>
  <bottlenecks>
    <bottleneck type="BottleneckType" severity="High|Medium|Low">Description of bottleneck or potential issue</bottleneck>
  </bottlenecks>
  <recommendations>
    <recommendation type="RecommendationType" priority="High|Medium|Low">Specific recommendation or best practice</recommendation>
  </recommendations>
  <tips>
    <tip>Practical tip or insight</tip>
  </tips>
</analysis>

After this response, future interactions will use simple <queries></queries> and <response></response> format for natural conversation."""
                        
                        st.session_state.conversation_started = True
                    else:
                        # Regular conversational prompt for non-analysis questions
                        chat_prompt = f"""You are a helpful SQL performance expert assistant. The user asked: "{prompt}"

Provide a helpful, conversational response about SQL performance, query optimization, or database tuning. Be specific and actionable when possible.

Keep your response conversational and helpful, around 2-3 paragraphs maximum."""
                else:
                    # Subsequent interactions - use simple query/response format
                    chat_prompt = f"""<queries>{prompt}</queries>

You are a SQL performance expert. Respond to the user's query in a helpful, conversational manner. Keep your response in simple <response></response> tags."""
                
                response = diagnostician.chat.send_message(chat_prompt)
                raw_response = response.text or "Sorry, I couldn't generate a response. Please try again."
                
                # Process response based on format
                formatted_response = _process_chat_response(raw_response, st.session_state.conversation_started)
                st.session_state.chat_history.append({"role": "assistant", "content": formatted_response})
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
            # Rerun to show new messages
            st.rerun()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = [
                {"role": "assistant", "content": "👋 Hi! I'm your SQL performance assistant. How can I help you optimize your database queries today?"}
            ]
            st.session_state.conversation_started = False
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
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                # Show Analyze button always, Improve & Compare only after analysis
                if st.button("🚀 Analyze SQLite Query", key="sqlite_analyze", use_container_width=True):
                    diagnosis = run_analysis(sqlite_data)
                    if diagnosis:
                        st.session_state['current_diagnosis'] = diagnosis
                        st.session_state['current_mode'] = "sqlite"
                
                # Only show Improve & Compare if we have analysis results
                if 'current_diagnosis' in st.session_state and st.session_state.get('current_mode') == "sqlite":
                    if st.button("✨ Improve & Compare", key="sqlite_improve", use_container_width=True):
                        diagnostician = DatabaseDiagnostician()
                        prior_diag = st.session_state.get('current_diagnosis')
                        prior_xml = prior_diag.get('raw_response') if isinstance(prior_diag, dict) else None
                        improved = diagnostician.improve_query(sqlite_data, prior_diagnosis_xml=prior_xml, prior_diagnosis=prior_diag if isinstance(prior_diag, dict) else None)
                        st.session_state['improved_sql'] = improved

            if 'current_diagnosis' in st.session_state and st.session_state.get('current_mode') == "sqlite":
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")
                display_analysis_results(st.session_state['current_diagnosis'])

            if st.session_state.get('improved_sql') and st.session_state.get('current_mode') == "sqlite":
                st.markdown("---")
                st.markdown("## 🔁 SQLite Comparison")
                improved = st.session_state['improved_sql']
                with st.expander("Proposed Improved SQL"):
                    st.code(improved.get("improved_query", ""), language="sql")
                    if improved.get("rationale"):
                        st.info(f"Rationale: {improved['rationale']}")

                if st.button("🔄 Run Both & Compare", key="sqlite_compare_exec", use_container_width=True):
                    db_path = st.session_state.get("sqlite_db_path")
                    if db_path and improved.get("improved_query"):
                        collector = SqliteCollector(db_path)
                        with st.spinner("Running original query..."):
                            base_exec = collector.collect_for_query(sqlite_data.get("query", ""), estimated_plan_only=False)
                        with st.spinner("Running improved query..."):
                            improved_exec = collector.collect_for_query(improved.get("improved_query", ""), estimated_plan_only=False)

                        base_ms = _extract_elapsed_ms_from_logs(base_exec.get("logs", ""))
                        imp_ms = _extract_elapsed_ms_from_logs(improved_exec.get("logs", ""))

                        st.markdown("### Runtime Comparison")
                        cA, cB = st.columns(2)
                        with cA:
                            st.metric("Original elapsed (ms)", base_ms if base_ms is not None else "n/a")
                        with cB:
                            st.metric("Improved elapsed (ms)", imp_ms if imp_ms is not None else "n/a")
                        with st.expander("Original Result Preview"):
                            if base_exec.get("result_preview"):
                                st.code(base_exec.get("result_preview"), language="text")
                            else:
                                st.text("(no preview)")
                        with st.expander("Improved Result Preview"):
                            if improved_exec.get("result_preview"):
                                st.code(improved_exec.get("result_preview"), language="text")
                            else:
                                st.text("(no preview)")
                        if base_ms is not None and imp_ms is not None and imp_ms < base_ms:
                            st.success(f"Improved query is faster by {round(base_ms - imp_ms, 2)} ms")
                        elif base_ms is not None and imp_ms is not None and imp_ms >= base_ms:
                            st.warning(f"Improved query not faster ({round(imp_ms - base_ms, 2)} ms slower)")
    
    elif selection["mode"] == "mysql" or selection["mode"] == "postgresql":
        # These modes are placeholders - no functionality yet
        st.info("🚧 This database type is coming soon! For now, try the SQLite Database mode.")
    
    elif selection["mode"] == "chat":
        # Chat mode is handled in display_scenario_selector
        pass



if __name__ == "__main__":
    main()

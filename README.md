# 🔍 AI-Powered Database Observability System

An intelligent database performance monitoring and optimization system that leverages Google's Gemini AI to automatically diagnose performance issues and provide actionable optimization recommendations.

## 🎯 Project Overview

Traditional database performance optimization requires expert DBAs to manually analyze query plans, logs, and statistics—a time-consuming process that can take hours or days. This system automates that expertise by using AI to instantly analyze database performance issues and provide specific, actionable recommendations.

### ✨ Key Features

- **🤖 AI-Powered Analysis**: Uses Google's Gemini LLM for expert-level database diagnostics
- **🔄 Recursive Query Improvement**: Iteratively improve SQL queries using previous results and comprehensive diagnostics
- **📊 Performance Progress Tracking**: Visual charts showing SQL enhancement progress across iterations
- **🏗️ Structured XML Prompting**: Ensures consistent, parseable analysis outputs
- **📊 Multi-Interface Support**: Both CLI and beautiful web interface (Streamlit)
- **💬 AI Chat Assistant**: Interactive chat with SQL performance expert - structured analysis for first query, then natural conversation
- **🔧 Multiple Database Support**: SQLite, PostgreSQL, SQL Server collectors
- **⚡ Real-time Analysis**: Instant performance bottleneck identification
- **📈 Actionable Recommendations**: Specific SQL commands and optimization strategies
- **🎨 Swiss Design UI**: Clean, minimal web interface for easy visualization
- **🔒 Clean Output**: XML tags hidden from users - only clean, formatted responses shown

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd e6data_hackathon
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env and add your Gemini API key
   echo "GEMINI_API_KEY=your_actual_api_key_here" > .env
   ```

### Running the System

#### Option 1: Command Line Interface
```bash
python db_observability.py
```

This will:
- Analyze sample database scenarios
- Generate detailed reports in the `output/` directory  
- Print a quick summary to console

#### Option 2: Web Interface
```bash
streamlit run streamlit_app.py
```

Then open your browser to `http://localhost:8501` for an interactive web interface.

## 📁 Project Architecture

```
e6data_hackathon/
├── 🔧 Core System
│   ├── db_observability.py      # Main system orchestrator
│   ├── gemini_client.py         # LLM client and prompting logic
│   ├── xml_utils.py            # XML input/output processing
│   └── fake_db_data.py         # Sample database scenarios
├── 🌐 Interfaces  
│   └── streamlit_app.py        # Swiss-design web interface
├── 📊 Data Collectors
│   ├── collectors/
│   │   ├── sqlite_collector.py    # SQLite database collector
│   │   └── sqlserver_collector.py # SQL Server collector
├── ⚙️ Configuration
│   ├── requirements.txt        # Dependencies
│   ├── env.example            # Environment template
│   └── .gitignore            # Git ignore rules
└── 📈 Output & Examples
    ├── output/               # Generated analysis reports
    └── example_output/       # Sample analysis results
```

## 🔍 How It Works

### 1. Data Collection
The system accepts various types of database information:
- **Query**: Raw SQL statements
- **Explain Plans**: Query execution plans (PostgreSQL, MySQL, etc.)
- **Logs**: Query logs, slow query logs, error logs
- **Schema**: Table definitions, indexes, constraints
- **Statistics**: Row counts, table sizes, cardinalities
- **Configuration**: Database parameters and settings
- **System Metrics**: CPU, memory, I/O statistics

### 2. AI Analysis Pipeline
```
Database Info → XML Structuring → Gemini AI → Structured Analysis → Human Reports
```

1. **XML Input Formatting**: All database information is structured into standardized XML tags
2. **LLM Prompting**: Gemini AI analyzes the data using expert database knowledge
3. **Structured Output**: AI returns diagnosis in predictable XML format
4. **Report Generation**: System parses XML and creates readable reports

### 3. Output Analysis
Each analysis provides:
- **🧠 Reasoning**: Detailed 2-3 paragraph explanation of the performance issues
- **⚠️ Root Causes**: Categorized list of identified problems
- **💡 Recommendations**: Specific actionable solutions with SQL examples
- **📝 Additional Comments**: Tips, monitoring suggestions, and best practices

### 4. Recursive Query Improvement Workflow
The system now supports iterative query optimization:

1. **🔍 Collect Diagnostics**: Gather comprehensive database information
2. **📊 Analyze Performance**: AI analyzes bottlenecks and provides recommendations
3. **✨ Generate Improved Query**: AI creates optimized version using analysis insights
4. **🔄 Run & Compare**: Execute both queries and measure performance improvements
5. **📈 Recursive Enhancement**: Use results to generate even better queries iteratively
6. **📊 Progress Visualization**: View improvement trends across iterations

#### Key Benefits:
- **Iterative Refinement**: Each improvement builds on previous optimizations
- **Comprehensive Context**: Uses all available diagnostics (schema, logs, stats) in each iteration
- **Performance Tracking**: Visual charts show progress over time
- **Automated Comparison**: Instant execution time comparisons between iterations

## 📊 Sample Analysis

Here's what the system analyzes:

### Input: Slow Query
```sql
SELECT o.order_id, o.customer_id, o.order_date, o.total_amount
FROM orders o
WHERE o.created_at >= '2024-01-01' 
AND o.created_at <= '2024-12-31'
AND o.status = 'completed'
ORDER BY o.total_amount DESC
LIMIT 100;
```

### Output: AI Diagnosis
**🔍 Analysis:**
"This query is performing a sequential scan on 1,000,000 rows with no index support. The execution time of 2.847 seconds is extremely poor for what should be a simple filtered query..."

**⚠️ Root Causes:**
- Missing index on `created_at` column
- Missing index on `status` column  
- Missing index on `total_amount` column
- Outdated table statistics

**💡 Recommendations:**
```sql
-- Create composite index for filtering
CREATE INDEX idx_orders_created_at_status 
ON orders(created_at, status) 
WHERE status = 'completed';

-- Create index for sorting
CREATE INDEX idx_orders_total_amount 
ON orders(total_amount DESC);

-- Update statistics
ANALYZE orders;
```

## 🎨 Web Interface Features

The Streamlit web interface offers:

- **🎯 Swiss Design Aesthetic**: Clean, minimal, typography-focused design
- **📊 Interactive Analysis**: Upload your own queries or use sample scenarios
- **💬 Smart AI Chat Assistant**: 
  - First interaction provides structured analysis with bottlenecks, recommendations, and tips
  - Subsequent conversations use natural language with clean formatting
  - All XML tags automatically hidden from users
  - Seamless conversation flow with `<queries>` and `<response>` handling
- **📈 Real-time Processing**: Watch analysis happen in real-time
- **💾 Export Results**: Download analysis reports
- **🔄 Multiple Database Support**: Switch between different database types
- **📱 Responsive Design**: Works on desktop and mobile

### Interface Screenshots

The web interface provides:
1. **Input Section**: Paste your query, explain plan, schema
2. **Analysis Dashboard**: Real-time AI processing with progress indicators  
3. **Results Visualization**: Structured cards showing reasoning, causes, recommendations
4. **Export Options**: Download detailed reports in multiple formats

## 🛠️ Advanced Usage

### Custom Database Scenarios

Create your own database scenarios:

```python
from fake_db_data import SAMPLE_DATA

# Add your scenario
SAMPLE_DATA["my_slow_query"] = {
    "query": "YOUR SQL QUERY HERE",
    "explain": "EXPLAIN PLAN OUTPUT HERE", 
    "schema": "TABLE SCHEMA HERE",
    "logs": "RELEVANT LOG ENTRIES HERE",
    "stats": "TABLE STATISTICS HERE"
}
```

### Real Database Integration

Connect to real databases using the collectors:

```python
from collectors.sqlite_collector import SqliteCollector

# Collect real data from SQLite
collector = SqliteCollector("path/to/your/database.db")
query_data = collector.collect_query_info("YOUR_QUERY_HERE")

# Analyze with AI
diagnostician = DatabaseDiagnostician()
diagnosis = diagnostician.analyze_scenario(query_data)
```

### Batch Processing

Analyze multiple queries at once:

```python
system = DBObservabilitySystem()
system.initialize()

# Analyze all scenarios
results = system.analyze_all_scenarios()

# Save all results
system.save_results_to_files("my_analysis_output/")
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING) | No |
| `DEBUG_MODE` | Enable debug output | No |

### Model Configuration

The system uses Gemini with optimized settings:
- **Model**: `gemini-1.5-flash` (free tier with high quotas)
- **Temperature**: `0.3` (consistent analysis)
- **Max Tokens**: `4096` (detailed responses)
- **Response Format**: Structured XML

## 📈 Sample Scenarios

The system includes realistic test scenarios:

### 1. Slow SELECT Without Index
- **Problem**: 2.8s execution time on 1M row table scan
- **Cause**: Missing indexes on filter/sort columns
- **Solution**: Composite and covering indexes

### 2. Inefficient JOIN Query  
- **Problem**: Complex join causing memory spilling
- **Cause**: Poor join order and missing indexes
- **Solution**: Index optimization and query rewriting

## 🧪 Testing

### Test API Connection
```bash
python gemini_client.py
```

### Run Sample Analysis
```bash
python db_observability.py
```

### Test Web Interface
```bash
streamlit run streamlit_app.py
```

## 🛣️ Roadmap & Future Enhancements

### Phase 2: Enhanced Analysis
- [ ] **Multi-database Support**: MySQL, Oracle, MongoDB
- [ ] **Real-time Monitoring**: Continuous performance tracking
- [ ] **Historical Analysis**: Trend analysis and performance regression detection
- [ ] **Cost Analysis**: Query cost estimation and optimization ROI

### Phase 3: Advanced Features  
- [x] **Conversational AI**: "Why is my query slow?" natural language interface ✅ COMPLETED
- [ ] **Automated Testing**: Simulate recommendation impact before implementation
- [ ] **Performance Benchmarking**: Before/after performance comparisons
- [ ] **Integration APIs**: Webhook support for CI/CD pipelines

### Phase 4: Enterprise Features
- [ ] **Multi-tenant Architecture**: Support for multiple databases/environments
- [ ] **Role-based Access**: Team collaboration and permissions
- [ ] **Alert System**: Proactive performance issue detection
- [ ] **Recommendation Tracking**: Monitor implemented optimizations

## 🤝 Contributing

We welcome contributions! Areas where help is needed:

- **Database Collectors**: Add support for more database types
- **Analysis Templates**: Improve XML prompting templates  
- **Test Scenarios**: Add more realistic database scenarios
- **UI/UX**: Enhance the web interface design
- **Documentation**: Improve guides and examples

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Google Gemini AI**: Powering the intelligent analysis engine
- **Streamlit**: Enabling rapid web interface development  
- **Database Community**: Inspiration from real-world performance challenges
- **Open Source**: Built on the shoulders of amazing open source tools

## 📞 Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Email**: [Contact the maintainers](mailto:your-email@example.com)

---

<div align="center">

**🔍 AI-Powered Database Observability System**

*Making database performance optimization accessible to everyone*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google AI](https://img.shields.io/badge/Google%20AI-4285F4?logo=google&logoColor=white)](https://ai.google/)

</div>
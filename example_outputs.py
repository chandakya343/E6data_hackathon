"""
Generate example outputs for demonstration purposes.
Creates mock LLM responses and formatted output files.
"""

import os
from datetime import datetime
from fake_db_data import SAMPLE_DATA
from xml_utils import parse_diagnosis_xml, format_diagnosis_output


def create_mock_llm_response_1() -> str:
    """Mock LLM response for the slow SELECT scenario."""
    
    return """<diagnosis>
  <reasoning>
    <![CDATA[
    This query is attempting to retrieve the top 100 orders by total amount for the year 2024, filtering by completed status. The performance issue is immediately apparent from the explain plan: the query is performing a sequential scan on the entire orders table (1,000,000 rows) with no index support.

    The execution time of 2.847 seconds is extremely poor for what should be a simple filtered query. The sequential scan is reading all rows and applying filters in memory, which is highly inefficient. The system is spending 99% of its time doing unnecessary I/O operations, scanning 850,000 rows that don't match the filter criteria.

    The root cause is the absence of appropriate indexes on the filtering and sorting columns (created_at, status, total_amount). Additionally, the query statistics show that the table hasn't been analyzed recently, which could impact the query planner's decisions, though the primary issue remains the missing indexes.
    ]]>
  </reasoning>

  <root_causes>
    <root_cause type="MissingIndex">
      No index exists on created_at column, forcing full table scan for date range filter
    </root_cause>
    <root_cause type="MissingIndex">
      No index on status column, preventing efficient filtering of completed orders
    </root_cause>
    <root_cause type="MissingIndex">
      No index on total_amount column, requiring expensive sort operation on unindexed data
    </root_cause>
    <root_cause type="StatisticsOutdated">
      Table statistics are 5 days old, potentially affecting query planner decisions
    </root_cause>
  </root_causes>

  <recommendations>
    <recommendation type="CreateIndex">
      CREATE INDEX idx_orders_created_at_status ON orders(created_at, status) WHERE status = 'completed';
    </recommendation>
    <recommendation type="CreateIndex">
      CREATE INDEX idx_orders_total_amount ON orders(total_amount DESC);
    </recommendation>
    <recommendation type="UpdateStatistics">
      ANALYZE orders; -- Update table statistics for better query planning
    </recommendation>
    <recommendation type="RewriteQuery">
      Consider adding LIMIT with ORDER BY earlier in processing: use a covering index with (created_at, status, total_amount, order_id, customer_id, order_date)
    </recommendation>
  </recommendations>

  <comments>
    <comment>Monitor query performance after index creation - expect 100x+ improvement</comment>
    <comment>Consider partitioning the orders table by created_at if it continues to grow rapidly</comment>
    <comment>Set up automated ANALYZE jobs to run weekly on high-volume tables</comment>
  </comments>
</diagnosis>"""


def create_mock_llm_response_2() -> str:
    """Mock LLM response for the inefficient JOIN scenario."""
    
    return """<diagnosis>
  <reasoning>
    <![CDATA[
    This query performs a complex aggregation joining customers and orders tables, but is suffering from severe performance issues due to multiple design problems. The 4.5 second execution time and creation of temporary files indicate that the query is exceeding available memory and spilling to disk.

    The main issue is the lack of a foreign key index on orders.customer_id, forcing a hash join that can't efficiently leverage existing indexes. The hash table for customers (65,536 buckets, 8 batches) shows memory pressure, and the external merge sorts confirm that work_mem (4MB) is insufficient for this operation. The query is processing 2 million rows in the join phase when proper indexing could dramatically reduce this.

    Additionally, the GROUP BY operation requires sorting 2 million intermediate results, and the HAVING clause filtering happens after expensive aggregation rather than during. The combination of these factors creates a perfect storm of inefficiency, with the database resorting to disk-based operations throughout the execution pipeline.
    ]]>
  </reasoning>

  <root_causes>
    <root_cause type="MissingIndex">
      Missing foreign key index on orders.customer_id prevents efficient join execution
    </root_cause>
    <root_cause type="ConfigurationIssue">
      work_mem (4MB) too small for hash operations, forcing expensive disk spills
    </root_cause>
    <root_cause type="SuboptimalQuery">
      HAVING clause forces aggregation of all data before filtering high-order customers
    </root_cause>
    <root_cause type="InappropriateJoin">
      Hash join strategy inefficient without proper indexing on join columns
    </root_cause>
  </root_causes>

  <recommendations>
    <recommendation type="CreateIndex">
      CREATE INDEX idx_orders_customer_id ON orders(customer_id);
    </recommendation>
    <recommendation type="CreateIndex">
      CREATE INDEX idx_customers_registration_date ON customers(registration_date) WHERE registration_date >= '2023-01-01';
    </recommendation>
    <recommendation type="ConfigChange">
      SET work_mem = '16MB'; -- Increase memory for hash operations
    </recommendation>
    <recommendation type="RewriteQuery">
      Use window functions or CTEs to pre-filter customers with >5 orders before joining
    </recommendation>
    <recommendation type="SchemaOptimization">
      Consider materialized view for customer order summaries if this query runs frequently
    </recommendation>
  </recommendations>

  <comments>
    <comment>Monitor memory usage after work_mem increase to ensure it doesn't cause overall system memory pressure</comment>
    <comment>The customer order count distribution shows heavy skew - consider separate optimization strategies for high-volume customers</comment>
    <comment>After indexing, consider using EXPLAIN (ANALYZE, BUFFERS) to verify reduced I/O</comment>
  </comments>
</diagnosis>"""


def generate_example_outputs():
    """Generate example output files showing what the system would produce."""
    
    # Create output directory
    output_dir = "/Users/aryanchandak/projects/e6data_hackathon/example_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Mock responses
    mock_responses = {
        "slow_select_without_index": create_mock_llm_response_1(),
        "inefficient_join": create_mock_llm_response_2()
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_files = []
    
    # Generate individual analysis files
    for scenario_name, mock_xml in mock_responses.items():
        diagnosis = parse_diagnosis_xml(mock_xml)
        formatted_output = format_diagnosis_output(diagnosis)
        
        # Create filename
        filename = f"{scenario_name}_analysis_example_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"DB OBSERVABILITY ANALYSIS REPORT (EXAMPLE)\n")
            f.write(f"Scenario: {scenario_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n\n")
            f.write(formatted_output)
            
            # Add raw data for context
            f.write(f"\n\n{'='*80}\n")
            f.write(f"ORIGINAL QUERY AND EXPLAIN PLAN\n")
            f.write(f"{'='*80}\n")
            f.write(f"Query:\n{SAMPLE_DATA[scenario_name].get('query', 'N/A')}\n\n")
            f.write(f"Explain Plan:\n{SAMPLE_DATA[scenario_name].get('explain', 'N/A')}\n\n")
            
            f.write(f"\n{'='*80}\n")
            f.write(f"RAW LLM XML RESPONSE (EXAMPLE)\n")
            f.write(f"{'='*80}\n")
            f.write(mock_xml)
        
        created_files.append(filepath)
        print(f"✅ Created example output: {filepath}")
    
    # Generate summary file
    summary_file = os.path.join(output_dir, f"summary_example_{timestamp}.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("DB OBSERVABILITY SYSTEM - EXAMPLE ANALYSIS SUMMARY\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*80}\n\n")
        f.write("This is an example output showing what the system would produce\n")
        f.write("when connected to the Gemini API with real database scenarios.\n\n")
        
        for scenario_name, mock_xml in mock_responses.items():
            diagnosis = parse_diagnosis_xml(mock_xml)
            
            f.write(f"SCENARIO: {scenario_name}\n")
            f.write(f"{'-'*40}\n")
            
            # Quick summary
            root_causes = diagnosis.get("root_causes", [])
            recommendations = diagnosis.get("recommendations", [])
            
            f.write(f"Root Causes Found: {len(root_causes)}\n")
            for cause in root_causes:
                f.write(f"  • {cause.get('type', 'Unknown')}: {cause.get('description', '')[:100]}...\n")
            
            f.write(f"Recommendations: {len(recommendations)}\n")
            for rec in recommendations:
                f.write(f"  • {rec.get('type', 'Unknown')}: {rec.get('description', '')[:100]}...\n")
            
            f.write("\n")
    
    created_files.append(summary_file)
    print(f"📊 Created example summary: {summary_file}")
    
    # Create system info file
    info_file = os.path.join(output_dir, "system_info.txt")
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write("DB OBSERVABILITY SYSTEM V1 - SYSTEM INFORMATION\n")
        f.write(f"{'='*60}\n\n")
        f.write("🎯 WHAT THIS SYSTEM DOES:\n")
        f.write("- Analyzes database performance issues using AI\n")
        f.write("- Identifies root causes of slow queries\n")
        f.write("- Provides specific, actionable recommendations\n")
        f.write("- Outputs structured analysis reports\n\n")
        
        f.write("🔧 HOW IT WORKS:\n")
        f.write("1. Takes database information (query, explain plan, schema, logs)\n")
        f.write("2. Formats data into structured XML for the LLM\n")
        f.write("3. Sends to Gemini AI for expert analysis\n")
        f.write("4. Parses XML response into structured diagnosis\n")
        f.write("5. Generates human-readable reports\n\n")
        
        f.write("📊 SAMPLE SCENARIOS ANALYZED:\n")
        for scenario_name in SAMPLE_DATA.keys():
            query_first_line = SAMPLE_DATA[scenario_name]['query'].strip().split('\n')[0]
            f.write(f"- {scenario_name}: {query_first_line}...\n")
        
        f.write(f"\n🚀 TO RUN WITH REAL API:\n")
        f.write("1. Get Gemini API key from Google AI Studio\n")
        f.write("2. Create .env file with GEMINI_API_KEY=your_key\n")
        f.write("3. Run: python db_observability.py\n")
        f.write("4. Check output/ directory for results\n")
    
    created_files.append(info_file)
    print(f"ℹ️  Created system info: {info_file}")
    
    return created_files


if __name__ == "__main__":
    print("🎭 Generating example outputs...")
    files = generate_example_outputs()
    print(f"\n✅ Generated {len(files)} example files")
    print("📁 Check the 'example_output/' directory for sample analysis results")

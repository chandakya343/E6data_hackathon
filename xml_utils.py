"""
XML utilities for structuring input/output with the LLM.
Handles creation of XML input tags and parsing of XML output tags.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import html


def create_input_xml(data: Dict[str, str]) -> str:
    """
    Create XML input structure for the LLM based on available data.
    
    Args:
        data: Dictionary containing database information
        
    Returns:
        XML string with all input tags
    """
    
    # Create root element
    root = ET.Element("database_info")
    
    # Define all possible input tags
    input_tags = [
        "query", "explain", "logs", "schema", 
        "stats", "config", "system"
    ]
    
    # Add each tag, even if empty
    for tag in input_tags:
        element = ET.SubElement(root, tag)
        if tag in data and data[tag]:
            # Use CDATA for content that might contain special characters
            element.text = data[tag].strip()
        else:
            element.text = ""
    
    # Convert to string
    xml_str = ET.tostring(root, encoding='unicode')
    
    # Pretty format manually (since we want to preserve CDATA sections)
    formatted_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    formatted_xml += xml_str.replace('><', '>\n<')
    
    return formatted_xml


def parse_diagnosis_xml(xml_response: str) -> Dict[str, any]:
    """
    Parse the LLM's XML response into structured data.
    
    Args:
        xml_response: XML string from LLM
        
    Returns:
        Dictionary with parsed diagnosis information
    """
    
    result = {
        "reasoning": "",
        "bottlenecks": [],
        "root_causes": [],
        "recommendations": [],
        "comments": []
    }
    
    try:
        # Extract the diagnosis section
        start_tag = "<diagnosis>"
        end_tag = "</diagnosis>"
        
        start_idx = xml_response.find(start_tag)
        end_idx = xml_response.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("Could not find <diagnosis> tags in response")
        
        diagnosis_xml = xml_response[start_idx:end_idx + len(end_tag)]
        
        # Parse XML
        root = ET.fromstring(diagnosis_xml)
        
        # Extract reasoning
        reasoning_elem = root.find("reasoning")
        if reasoning_elem is not None and reasoning_elem.text:
            result["reasoning"] = reasoning_elem.text.strip()
        
        # Extract bottlenecks
        bottlenecks_elem = root.find("bottlenecks")
        if bottlenecks_elem is not None:
            for bottleneck_elem in bottlenecks_elem.findall("bottleneck"):
                bottleneck_type = bottleneck_elem.get("type", "Unknown")
                bottleneck_severity = bottleneck_elem.get("severity", "Medium")
                bottleneck_text = bottleneck_elem.text.strip() if bottleneck_elem.text else ""
                result["bottlenecks"].append({
                    "type": bottleneck_type,
                    "severity": bottleneck_severity,
                    "description": bottleneck_text
                })
        
        # Extract root causes
        root_causes_elem = root.find("root_causes")
        if root_causes_elem is not None:
            for cause_elem in root_causes_elem.findall("root_cause"):
                cause_type = cause_elem.get("type", "Unknown")
                cause_text = cause_elem.text.strip() if cause_elem.text else ""
                result["root_causes"].append({
                    "type": cause_type,
                    "description": cause_text
                })
        
        # Extract recommendations
        recommendations_elem = root.find("recommendations")
        if recommendations_elem is not None:
            for rec_elem in recommendations_elem.findall("recommendation"):
                rec_type = rec_elem.get("type", "Unknown")
                rec_priority = rec_elem.get("priority", "Medium")
                rec_text = rec_elem.text.strip() if rec_elem.text else ""
                result["recommendations"].append({
                    "type": rec_type,
                    "priority": rec_priority,
                    "description": rec_text
                })
        
        # Extract comments
        comments_elem = root.find("comments")
        if comments_elem is not None:
            for comment_elem in comments_elem.findall("comment"):
                comment_text = comment_elem.text.strip() if comment_elem.text else ""
                if comment_text:
                    result["comments"].append(comment_text)
    
    except Exception as e:
        # Fallback: try to extract reasoning text manually
        reasoning_start = xml_response.find("<reasoning>")
        reasoning_end = xml_response.find("</reasoning>")
        
        if reasoning_start != -1 and reasoning_end != -1:
            reasoning_start += len("<reasoning>")
            reasoning_text = xml_response[reasoning_start:reasoning_end].strip()
            
            # Remove CDATA wrapper if present
            if reasoning_text.startswith("<![CDATA[") and reasoning_text.endswith("]]>"):
                reasoning_text = reasoning_text[9:-3].strip()
            
            result["reasoning"] = reasoning_text
        
        result["parse_error"] = str(e)
        result["raw_response"] = xml_response
    
    return result


def format_diagnosis_output(diagnosis: Dict[str, any]) -> str:
    """
    Format the parsed diagnosis into a readable text output.
    
    Args:
        diagnosis: Parsed diagnosis dictionary
        
    Returns:
        Formatted text string
    """
    
    output = []
    output.append("=" * 80)
    output.append("DATABASE PERFORMANCE DIAGNOSIS")
    output.append("=" * 80)
    output.append("")
    
    # Reasoning section
    if diagnosis.get("reasoning"):
        output.append("🔍 ANALYSIS & REASONING")
        output.append("-" * 40)
        output.append(diagnosis["reasoning"])
        output.append("")
    
    # Bottlenecks section
    if diagnosis.get("bottlenecks"):
        output.append("🚨 PERFORMANCE BOTTLENECKS")
        output.append("-" * 40)
        for i, bottleneck in enumerate(diagnosis["bottlenecks"], 1):
            severity = bottleneck.get('severity', 'Medium')
            severity_icon = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(severity, "🟠")
            output.append(f"{i}. {severity_icon} {bottleneck['type']} ({severity}): {bottleneck['description']}")
        output.append("")
    
    # Root causes section
    if diagnosis.get("root_causes"):
        output.append("⚠️  ROOT CAUSES IDENTIFIED")
        output.append("-" * 40)
        for i, cause in enumerate(diagnosis["root_causes"], 1):
            output.append(f"{i}. {cause['type']}: {cause['description']}")
        output.append("")
    
    # Recommendations section
    if diagnosis.get("recommendations"):
        output.append("💡 RECOMMENDATIONS")
        output.append("-" * 40)
        for i, rec in enumerate(diagnosis["recommendations"], 1):
            output.append(f"{i}. {rec['type']}: {rec['description']}")
        output.append("")
    
    # Comments section
    if diagnosis.get("comments"):
        output.append("📝 ADDITIONAL COMMENTS")
        output.append("-" * 40)
        for comment in diagnosis["comments"]:
            output.append(f"• {comment}")
        output.append("")
    
    # Error information if present
    if diagnosis.get("parse_error"):
        output.append("⚠️  PARSING ERROR")
        output.append("-" * 40)
        output.append(f"Error: {diagnosis['parse_error']}")
        output.append("")
        
        if diagnosis.get("raw_response"):
            output.append("Raw LLM Response:")
            output.append(diagnosis["raw_response"])
            output.append("")
    
    output.append("=" * 80)
    
    return "\n".join(output)


def create_system_prompt() -> str:
    """
    Create the system prompt that instructs the LLM on XML format.
    
    Returns:
        System prompt string
    """
    
    return """You are an expert SQL diagnostic assistant specialized in database performance analysis. 

You will receive database information in XML format containing query, explain plan, logs, schema, statistics, configuration, and system metrics.

You must ALWAYS respond with your analysis in the following XML structure:

<diagnosis>
  <reasoning>
    <![CDATA[
    Provide detailed reasoning here. This should be 2-3 paragraphs explaining:
    1. What the query is trying to do
    2. What performance issues you identified
    3. Why these issues are occurring
    ]]>
  </reasoning>

  <bottlenecks>
    <bottleneck type="CategoryName" severity="High|Medium|Low">
      Description of the specific performance bottleneck
    </bottleneck>
    <!-- Add more bottleneck elements as needed -->
  </bottlenecks>

  <root_causes>
    <root_cause type="CategoryName">
      Brief description of the issue
    </root_cause>
    <!-- Add more root_cause elements as needed -->
  </root_causes>

  <recommendations>
    <recommendation type="CategoryName" priority="High|Medium|Low">
      Specific actionable recommendation with SQL/config if applicable
    </recommendation>
    <!-- Add more recommendation elements as needed -->
  </recommendations>

  <comments>
    <comment>Additional tips or considerations</comment>
    <!-- Add more comment elements as needed -->
  </comments>
</diagnosis>

Common bottleneck types: IOBottleneck, CPUBottleneck, MemoryBottleneck, IndexBottleneck, JoinBottleneck, SortBottleneck, LockingBottleneck
Common root_cause types: MissingIndex, InappropriateJoin, FullTableScan, SuboptimalQuery, ConfigurationIssue, StatisticsOutdated
Common recommendation types: CreateIndex, RewriteQuery, UpdateStatistics, ConfigChange, SchemaOptimization

Always provide reasoning first, then identify bottlenecks with severity, then root causes, then prioritized recommendations."""

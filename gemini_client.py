"""
Gemini LLM client for database observability analysis.
Handles API communication and XML-based structured prompting.
"""

import google.generativeai as genai
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from xml_utils import create_input_xml, parse_diagnosis_xml, create_system_prompt

# Load environment variables from .env file
load_dotenv()


class DatabaseDiagnostician:
    """
    AI-powered database performance diagnostician using Gemini LLM.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the diagnostician.
        
        Args:
            api_key: Gemini API key. If None, reads from environment variable.
        """
        
        # Configure API key
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set or api_key not provided")
        
        genai.configure(api_key=api_key)
        
        # Configure model parameters
        self.generation_config = {
            "temperature": 0.3,          # Lower temperature for more consistent analysis
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 4096,   # Enough for detailed analysis
            "response_mime_type": "text/plain",
        }
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",  # Free tier model with higher quota
            generation_config=self.generation_config,
        )
        
        # Start chat session with system prompt
        self.chat = self.model.start_chat(
            history=[{
                "role": "user",
                "parts": [create_system_prompt()]
            }]
        )
    
    def analyze_performance(self, db_data: Dict[str, str]) -> Dict[str, any]:
        """
        Analyze database performance issues using the provided data.
        
        Args:
            db_data: Dictionary containing database information (query, explain, logs, etc.)
            
        Returns:
            Parsed diagnosis dictionary
        """
        
        try:
            # Create XML input
            xml_input = create_input_xml(db_data)
            
            print("Sending analysis request to Gemini...")
            print(f"Input XML preview (first 500 chars):\n{xml_input[:500]}...\n")
            
            # Send to LLM
            response = self.chat.send_message(xml_input)
            raw_response = response.text
            
            print("Received response from Gemini, parsing XML...")
            
            # Parse XML response
            diagnosis = parse_diagnosis_xml(raw_response)
            
            # Add metadata
            diagnosis["raw_input"] = xml_input
            diagnosis["raw_response"] = raw_response
            
            return diagnosis
            
        except Exception as e:
            return {
                "reasoning": f"Error occurred during analysis: {str(e)}",
                "root_causes": [],
                "recommendations": [],
                "comments": [],
                "error": str(e),
                "raw_input": db_data,
                "raw_response": ""
            }

    def improve_query(self, db_data: Dict[str, str], prior_diagnosis_xml: Optional[str] = None, prior_diagnosis: Optional[Dict[str, any]] = None) -> Dict[str, str]:
        """
        Ask the LLM to propose an improved SQL query given the same inputs.
        You can optionally pass prior diagnosis XML (from a previous analysis) for extra context.
        Returns a dict with keys: improved_query, rationale
        """
        try:
            # Reuse the same structured XML input to give full context
            xml_input = create_input_xml(db_data)
            context_parts = [xml_input]

            # Attach prior diagnosis if available
            if prior_diagnosis_xml and "<diagnosis>" in prior_diagnosis_xml:
                context_parts.append("\n<!-- prior_diagnosis -->\n" + prior_diagnosis_xml.strip())
            elif prior_diagnosis:
                # Minimal reconstruction if no raw XML is present
                diag_lines = ["<diagnosis>"]
                if prior_diagnosis.get("reasoning"):
                    diag_lines.append("  <reasoning>\n    <![CDATA[\n" + prior_diagnosis["reasoning"] + "\n    ]]>\n  </reasoning>")
                if prior_diagnosis.get("bottlenecks"):
                    diag_lines.append("  <bottlenecks>")
                    for b in prior_diagnosis["bottlenecks"]:
                        severity = b.get('severity', 'Medium')
                        diag_lines.append(f"    <bottleneck type=\"{b.get('type','Unknown')}\" severity=\"{severity}\">{b.get('description','')}</bottleneck>")
                    diag_lines.append("  </bottlenecks>")
                if prior_diagnosis.get("root_causes"):
                    diag_lines.append("  <root_causes>")
                    for c in prior_diagnosis["root_causes"]:
                        diag_lines.append(f"    <root_cause type=\"{c.get('type','Unknown')}\">{c.get('description','')}</root_cause>")
                    diag_lines.append("  </root_causes>")
                if prior_diagnosis.get("recommendations"):
                    diag_lines.append("  <recommendations>")
                    for r in prior_diagnosis["recommendations"]:
                        priority = r.get('priority', 'Medium')
                        diag_lines.append(f"    <recommendation type=\"{r.get('type','Unknown')}\" priority=\"{priority}\">{r.get('description','')}</recommendation>")
                    diag_lines.append("  </recommendations>")
                if prior_diagnosis.get("comments"):
                    diag_lines.append("  <comments>")
                    for cm in prior_diagnosis["comments"]:
                        diag_lines.append(f"    <comment>{cm}</comment>")
                    diag_lines.append("  </comments>")
                diag_lines.append("</diagnosis>")
                context_parts.append("\n".join(diag_lines))

            instruction = (
                "Given the provided <database_info> and optional <diagnosis> context, propose an improved SQL query that is semantically equivalent but more efficient based on the provided schema, stats, plans, logs, and recommendations.\n"
                "Respond in this exact format only:\n\n"
                "<improved>\n"
                "-- rationale: one or two sentences explaining the key changes\n"
                "```sql\n"
                "<your improved SQL here>\n"
                "```\n"
                "</improved>"
            )
            content = "\n\n".join(context_parts + [instruction])
            response = self.chat.send_message(content)
            raw = response.text or ""

            # naive parse
            rationale = ""
            improved_sql = ""
            # extract rationale after prefix
            if "-- rationale:" in raw:
                rationale = raw.split("-- rationale:", 1)[1].strip().split("```", 1)[0].strip()
            # extract code block
            code_start = raw.find("```sql")
            if code_start == -1:
                code_start = raw.find("```")
            if code_start != -1:
                code_start = raw.find("\n", code_start) + 1
                code_end = raw.find("```", code_start)
                if code_end != -1:
                    improved_sql = raw[code_start:code_end].strip()

            return {"improved_query": improved_sql, "rationale": rationale, "raw_response": raw}
        except Exception as e:
            return {"improved_query": "", "rationale": f"error: {e}", "raw_response": ""}
    
    def batch_analyze(self, datasets: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, any]]:
        """
        Analyze multiple database scenarios.
        
        Args:
            datasets: Dictionary of scenario_name -> db_data
            
        Returns:
            Dictionary of scenario_name -> diagnosis
        """
        
        results = {}
        
        for scenario_name, db_data in datasets.items():
            print(f"\n{'='*60}")
            print(f"Analyzing scenario: {scenario_name}")
            print(f"{'='*60}")
            
            results[scenario_name] = self.analyze_performance(db_data)
        
        return results


def test_connection() -> bool:
    """
    Test the Gemini API connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    
    try:
        # Load environment variables
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY environment variable not set")
            return False
        
        genai.configure(api_key=api_key)
        
        # Simple test
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Hello, this is a connection test.")
        
        if response.text:
            print("✅ Gemini API connection successful")
            return True
        else:
            print("❌ Gemini API connection failed - no response")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    test_connection()

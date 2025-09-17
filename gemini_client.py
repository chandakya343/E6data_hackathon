"""
Gemini LLM client for database observability analysis.
Handles API communication and XML-based structured prompting.
"""

import google.generativeai as genai
import os
import re
from typing import Dict, Optional
from dotenv import load_dotenv
from xml_utils import (
    create_input_xml,
    parse_diagnosis_xml,
    create_system_prompt,
    create_chat_system_prompt,
    build_chat_prompt,
    extract_response_from_text,
)

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
            model_name="gemini-2.5-flash",  # Latest model with improved performance
            generation_config=self.generation_config,
        )
        
        # Start chat sessions
        # 1) Analysis chat uses the structured diagnosis system prompt
        self.analysis_chat = self.model.start_chat(
            history=[{"role": "user", "parts": [create_system_prompt()]}]
        )
        # 2) Simplified chat uses the SQL master prompt and <history>/<user>/<response> protocol
        self.simple_chat = self.model.start_chat(
            history=[{"role": "user", "parts": [create_chat_system_prompt()]}]
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
            response = self.analysis_chat.send_message(xml_input)
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

    def improve_query(self, db_data: Dict[str, str], prior_diagnosis_xml: Optional[str] = None, prior_diagnosis: Optional[Dict[str, any]] = None, improvement_context: Optional[str] = None) -> Dict[str, str]:
        """
        Ask the LLM to propose an improved SQL query given the same inputs.
        Enhanced version supports recursive improvements with comprehensive context.
        
        Args:
            db_data: Database information including query, schema, logs, etc.
            prior_diagnosis_xml: Raw XML response from previous analysis
            prior_diagnosis: Parsed diagnosis dictionary from previous analysis
            improvement_context: Additional context about previous improvement iterations
            
        Returns:
            Dict with keys: improved_query, rationale, raw_response
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
            
            # Add improvement history context if available
            history_block = improvement_context or db_data.get("improvement_history")
            if history_block:
                context_parts.append(f"\n<!-- improvement_history -->\n{history_block}")
            
            # Enhanced instruction for recursive improvements
            if db_data.get("improvement_history"):
                instruction = (
                    "Given the provided <database_info>, <diagnosis> context, and improvement history, propose an even better SQL query that builds upon previous optimizations.\n"
                    "\n"
                    "RECURSIVE IMPROVEMENT GUIDELINES:\n"
                    "- Consider all previous iterations and their performance characteristics\n"
                    "- Look for additional optimization opportunities not addressed in previous iterations\n"
                    "- Consider advanced techniques like query restructuring, subquery optimization, or alternative algorithms\n"
                    "- Ensure the query remains semantically equivalent while improving performance\n"
                    "- Focus on bottlenecks identified in the diagnosis that may not have been fully addressed\n"
                    "\n"
                    "Respond in this exact format only:\n\n"
                    "<improved>\n"
                    "-- rationale: detailed explanation of the recursive improvements and why they should be more effective\n"
                    "```sql\n"
                    "<your recursively improved SQL here>\n"
                    "```\n"
                    "</improved>"
                )
            else:
                instruction = (
                    "Given the provided <database_info> and optional <diagnosis> context, propose an improved SQL query that is semantically equivalent but more efficient based on the provided schema, stats, plans, logs, and recommendations.\n"
                    "\n"
                    "RESPONSE RULES (STRICT):\n"
                    "- Return EXACTLY one improved SELECT statement only.\n"
                    "- Do NOT include DDL (CREATE INDEX, etc.), comments, explanations, or multiple statements.\n"
                    "- Keep the statement self-contained and runnable.\n"
                    "\n"
                    "Respond in this exact format only:\n\n"
                    "<improved>\n"
                    "-- rationale: one or two sentences explaining the key changes\n"
                    "```sql\n"
                    "<your improved SELECT here>\n"
                    "```\n"
                    "</improved>"
                )
            
            content = "\n\n".join(context_parts + [instruction])
            response = self.analysis_chat.send_message(content)
            raw = response.text or ""

            # Enhanced parsing to handle longer rationales and ensure SELECT-only
            rationale = ""
            improved_sql = ""
            
            # Extract rationale - more robust parsing
            if "-- rationale:" in raw:
                rationale_start = raw.find("-- rationale:") + len("-- rationale:")
                rationale_end = raw.find("```", rationale_start)
                if rationale_end != -1:
                    rationale = raw[rationale_start:rationale_end].strip()
            
            # Extract code block
            code_start = raw.find("```sql")
            if code_start == -1:
                code_start = raw.find("```")
            if code_start != -1:
                code_start = raw.find("\n", code_start) + 1
                code_end = raw.find("```", code_start)
                if code_end != -1:
                    improved_sql = raw[code_start:code_end].strip()

            # Cleanup: strip comments and extract only the first SELECT statement
            def _extract_first_select(sql_text: str) -> str:
                if not sql_text:
                    return ""
                txt = sql_text.strip()
                # Remove block comments and line comments
                txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.DOTALL)
                txt = re.sub(r"^\s*--.*$", "", txt, flags=re.MULTILINE)
                # Find first SELECT
                m = re.search(r"\bselect\b", txt, flags=re.IGNORECASE)
                if not m:
                    return ""
                sub = txt[m.start():]
                # Truncate at the first semicolon if present
                sc = sub.find(";")
                if sc != -1:
                    sub = sub[:sc+1]
                return sub.strip()

            cleaned = _extract_first_select(improved_sql)
            if cleaned:
                improved_sql = cleaned
            # If still not a SELECT, leave empty to be handled by caller
            if improved_sql and not re.match(r"^\s*select\b", improved_sql, flags=re.IGNORECASE):
                improved_sql = ""

            print(f"Generated {'recursive' if db_data.get('improvement_history') else 'initial'} improvement:")
            print(f"Rationale: {rationale[:200]}..." if len(rationale) > 200 else f"Rationale: {rationale}")
            print(f"Query length: {len(improved_sql)} characters")

            return {"improved_query": improved_sql, "rationale": rationale, "raw_response": raw}
        except Exception as e:
            print(f"Error in improve_query: {e}")
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

    def chat_respond(self, history: list, user_message: str) -> str:
        """
        Respond to a user chat message using the simplified protocol.

        Args:
            history: List of dicts with optional keys 'user' and 'response'
            user_message: The latest user message

        Returns:
            Cleaned response content (without tags), extracted from <response> ... </response>
        """
        prompt = build_chat_prompt(history=history, user_message=user_message)
        response = self.simple_chat.send_message(prompt)
        raw = response.text or ""
        return extract_response_from_text(raw)


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
        model = genai.GenerativeModel("gemini-2.5-flash")
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

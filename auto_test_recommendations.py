"""
Automatic Recommendation Testing Framework
Simulates the impact of recommendations without making permanent changes.
"""

import sqlite3
import time
from typing import Dict, List, Tuple
from collectors.sqlite_collector import SqliteCollector
from gemini_client import DatabaseDiagnostician

class RecommendationTester:
    """
    Automatically tests recommendations by simulating their impact.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.collector = SqliteCollector(db_path)
        
    def test_index_recommendation(self, original_query: str, index_sql: str) -> Dict[str, any]:
        """
        Test the impact of creating an index by:
        1. Creating a temporary database copy
        2. Adding the index
        3. Running the query and measuring performance
        4. Comparing with original performance
        """
        results = {
            "recommendation": index_sql,
            "original_time": None,
            "improved_time": None,
            "improvement_percent": None,
            "success": False,
            "error": None
        }
        
        try:
            # Get baseline performance
            baseline = self.collector.collect_for_query(original_query, estimated_plan_only=False)
            baseline_time = self._extract_time(baseline.get("logs", ""))
            results["original_time"] = baseline_time
            
            # Create temporary database with index
            temp_db = self._create_temp_db_with_index(index_sql)
            
            # Test with index
            temp_collector = SqliteCollector(temp_db)
            improved = temp_collector.collect_for_query(original_query, estimated_plan_only=False)
            improved_time = self._extract_time(improved.get("logs", ""))
            results["improved_time"] = improved_time
            
            # Calculate improvement
            if baseline_time and improved_time:
                improvement = ((baseline_time - improved_time) / baseline_time) * 100
                results["improvement_percent"] = round(improvement, 2)
                results["success"] = True
            
            # Cleanup temp database
            import os
            if os.path.exists(temp_db):
                os.remove(temp_db)
                
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    def _create_temp_db_with_index(self, index_sql: str) -> str:
        """Create a temporary copy of the database with the index added."""
        import shutil
        import tempfile
        import os
        
        # Create temp file
        temp_db = tempfile.mktemp(suffix=".db")
        
        # Copy original database
        shutil.copy2(self.db_path, temp_db)
        
        # Add index to temp database
        with sqlite3.connect(temp_db) as conn:
            conn.execute(index_sql)
            conn.commit()
            
        return temp_db
    
    def _extract_time(self, logs: str) -> float:
        """Extract execution time from logs."""
        import re
        try:
            match = re.search(r"Execution elapsed:\s*([0-9.]+)\s*ms", logs)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None
    
    def auto_test_all_recommendations(self, query: str, diagnosis: Dict[str, any]) -> List[Dict[str, any]]:
        """
        Automatically test all CREATE INDEX recommendations from a diagnosis.
        """
        test_results = []
        
        recommendations = diagnosis.get("recommendations", [])
        
        for rec in recommendations:
            if rec.get("type") == "CreateIndex" and "CREATE INDEX" in rec.get("description", ""):
                index_sql = rec.get("description", "")
                
                # Test this index recommendation
                result = self.test_index_recommendation(query, index_sql)
                result["recommendation_type"] = rec.get("type")
                result["priority"] = rec.get("priority", "Medium")
                
                test_results.append(result)
        
        return test_results


def simulate_recommendation_impact(db_path: str, query: str, diagnosis: Dict[str, any]) -> Dict[str, any]:
    """
    Main function to simulate the impact of all recommendations.
    """
    tester = RecommendationTester(db_path)
    
    # Test all index recommendations
    index_results = tester.auto_test_all_recommendations(query, diagnosis)
    
    # Calculate overall impact
    total_recommendations = len([r for r in diagnosis.get("recommendations", []) if r.get("type") == "CreateIndex"])
    successful_tests = len([r for r in index_results if r.get("success")])
    
    avg_improvement = 0
    if successful_tests > 0:
        improvements = [r.get("improvement_percent", 0) for r in index_results if r.get("success")]
        avg_improvement = sum(improvements) / len(improvements)
    
    return {
        "total_recommendations": total_recommendations,
        "successful_tests": successful_tests,
        "average_improvement": round(avg_improvement, 2),
        "detailed_results": index_results,
        "summary": f"Tested {successful_tests}/{total_recommendations} recommendations with {avg_improvement:.1f}% average improvement"
    }


if __name__ == "__main__":
    # Example usage
    print("🧪 Recommendation Testing Framework")
    print("This simulates the impact of SQL optimization recommendations")

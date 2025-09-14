"""
Main DB Observability System - AI-Powered Database Performance Analyzer
Core logic that ties together data, LLM client, and output generation.
"""

import os
from datetime import datetime
from typing import Dict, List
from fake_db_data import SAMPLE_DATA
from gemini_client import DatabaseDiagnostician, test_connection
from collectors.sqlserver_collector import SqlServerCollector
from xml_utils import format_diagnosis_output


class DBObservabilitySystem:
    """
    Main system that orchestrates database performance analysis.
    """
    
    def __init__(self):
        """Initialize the observability system."""
        self.diagnostician = None
        self.results = {}
    
    def initialize(self) -> bool:
        """
        Initialize the system and test connections.
        
        Returns:
            True if initialization successful, False otherwise
        """
        
        print("🔧 Initializing DB Observability System...")
        
        # Test API connection
        if not test_connection():
            print("❌ Failed to initialize: API connection failed")
            return False
        
        # Initialize diagnostician
        try:
            self.diagnostician = DatabaseDiagnostician()
            print("✅ Diagnostician initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize diagnostician: {e}")
            return False
    
    def analyze_all_scenarios(self) -> Dict[str, Dict]:
        """
        Analyze all sample scenarios.
        
        Returns:
            Dictionary of results for each scenario
        """
        
        if not self.diagnostician:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        print(f"\n🔍 Starting analysis of {len(SAMPLE_DATA)} scenarios...")
        
        # Run batch analysis
        self.results = self.diagnostician.batch_analyze(SAMPLE_DATA)
        
        print(f"✅ Analysis complete for all scenarios")
        return self.results
    
    def save_results_to_files(self, output_dir: str = "output") -> List[str]:
        """
        Save analysis results to text files.
        
        Args:
            output_dir: Directory to save output files
            
        Returns:
            List of created file paths
        """
        
        if not self.results:
            raise RuntimeError("No results to save. Run analyze_all_scenarios() first.")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        created_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for scenario_name, diagnosis in self.results.items():
            # Format the diagnosis
            formatted_output = format_diagnosis_output(diagnosis)
            
            # Create filename
            safe_name = scenario_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_analysis_{timestamp}.txt"
            filepath = os.path.join(output_dir, filename)
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"DB OBSERVABILITY ANALYSIS REPORT\n")
                f.write(f"Scenario: {scenario_name}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"{'='*80}\n\n")
                f.write(formatted_output)
                
                # Add raw data for debugging
                f.write(f"\n\n{'='*80}\n")
                f.write(f"RAW INPUT DATA\n")
                f.write(f"{'='*80}\n")
                f.write(f"Query:\n{SAMPLE_DATA[scenario_name].get('query', 'N/A')}\n\n")
                f.write(f"Explain Plan:\n{SAMPLE_DATA[scenario_name].get('explain', 'N/A')}\n\n")
                
                if diagnosis.get("raw_response"):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"RAW LLM RESPONSE\n")
                    f.write(f"{'='*80}\n")
                    f.write(diagnosis["raw_response"])
            
            created_files.append(filepath)
            print(f"💾 Saved analysis to: {filepath}")
        
        # Create summary file
        summary_file = os.path.join(output_dir, f"summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("DB OBSERVABILITY SYSTEM - ANALYSIS SUMMARY\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n\n")
            
            for scenario_name, diagnosis in self.results.items():
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
        print(f"📊 Saved summary to: {summary_file}")
        
        return created_files
    
    def print_quick_summary(self):
        """Print a quick summary to console."""
        
        if not self.results:
            print("No results available.")
            return
        
        print(f"\n📊 QUICK SUMMARY")
        print(f"{'='*50}")
        
        for scenario_name, diagnosis in self.results.items():
            print(f"\n🔍 {scenario_name}")
            print(f"{'-'*30}")
            
            # Show first paragraph of reasoning
            reasoning = diagnosis.get("reasoning", "No reasoning available")
            first_paragraph = reasoning.split('\n\n')[0] if reasoning else "No analysis"
            print(f"Analysis: {first_paragraph[:200]}...")
            
            # Show counts
            root_causes = diagnosis.get("root_causes", [])
            recommendations = diagnosis.get("recommendations", [])
            print(f"Issues Found: {len(root_causes)} | Recommendations: {len(recommendations)}")


def main():
    """Main function to run the DB observability analysis."""
    
    print("🚀 Starting DB Observability System V1")
    print("="*60)
    
    # Initialize system
    system = DBObservabilitySystem()
    
    if not system.initialize():
        print("❌ System initialization failed. Please check your GEMINI_API_KEY.")
        return
    
    try:
        # Default: run sample scenarios as before
        results = system.analyze_all_scenarios()
        system.print_quick_summary()
        created_files = system.save_results_to_files()
        print(f"\n🎉 Analysis Complete!")
        print(f"📁 {len(created_files)} files created in 'output/' directory")
        print(f"🔍 Check the files for detailed analysis results")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

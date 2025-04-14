#!/usr/bin/env python3
"""
Diagnostics module for SARYA.
Provides tools for self-diagnosis, monitoring, and health checks.
"""
import os
import json
import psutil
import logging
import datetime
import importlib
import importlib.util
import traceback
from typing import Dict, List, Any, Optional, Tuple

from core.base_module import BaseModule

logger = logging.getLogger(__name__)

class DiagnosticsModule(BaseModule):
    """
    Module for diagnosing and monitoring SARYA's health.
    """
    
    def __init__(self, module_id=None):
        """Initialize the DiagnosticsModule."""
        super().__init__(name="DiagnosticsModule")
        self.results = []
        self.diagnostics_path = "reflex_diagnosis_log.json"
        
    def _start(self) -> bool:
        """Start the diagnostics module."""
        return True
        
    def _stop(self) -> bool:
        """Stop the diagnostics module."""
        return True
    
    def _initialize(self) -> bool:
        """
        Initialize the diagnostics module.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Create diagnostics directory if it doesn't exist
            os.makedirs(os.path.dirname(self.diagnostics_path), exist_ok=True)
            logger.info("Diagnostics module initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing diagnostics module: {e}")
            return False
    
    def run_full_diagnosis(self) -> Dict[str, Any]:
        """
        Run a full system diagnosis.
        
        Returns:
            Dict with diagnostic results
        """
        logger.info("Starting full system diagnosis")
        self.results = []
        
        # Run individual diagnostic checks
        self.check_code_quality()
        self.check_system_health()
        self.check_module_dependencies()
        
        # Save results
        self.save_diagnostics()
        
        # Return summary
        return {
            "total_issues": len(self.results),
            "severity_counts": self._count_by_severity(),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    
    def check_code_quality(self) -> List[Dict[str, Any]]:
        """
        Check code quality by scanning for TODOs, placeholders, etc.
        
        Returns:
            List of code quality issues
        """
        logger.info("Checking code quality")
        issues = []
        
        for root, _, files in os.walk("."):
            # Skip directories that are likely to contain external code
            if any(skip_dir in root for skip_dir in [".git", "__pycache__", "venv", ".venv", "node_modules"]):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', errors='ignore') as f:
                            content = f.read()
                            
                            # Check for TODOs
                            if 'TODO' in content:
                                issues.append({
                                    "file": path,
                                    "issue": "Contains TODO comment",
                                    "severity": "low",
                                    "category": "code_quality",
                                    "detected_at": datetime.datetime.utcnow().isoformat()
                                })
                            
                            # Check for pass statements
                            if 'pass' in content:
                                issues.append({
                                    "file": path,
                                    "issue": "Contains pass placeholder",
                                    "severity": "low",
                                    "category": "code_quality",
                                    "detected_at": datetime.datetime.utcnow().isoformat()
                                })
                            
                            # Check for print statements (should use logging)
                            if 'print(' in content:
                                issues.append({
                                    "file": path,
                                    "issue": "Contains print statement (consider using logging)",
                                    "severity": "low",
                                    "category": "code_quality",
                                    "detected_at": datetime.datetime.utcnow().isoformat()
                                })
                    except Exception as e:
                        logger.error(f"Error checking file {path}: {e}")
        
        # Add issues to results
        self.results.extend(issues)
        logger.info(f"Found {len(issues)} code quality issues")
        return issues
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Check system health metrics.
        
        Returns:
            Dict with system health metrics
        """
        logger.info("Checking system health")
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check for concerning values
            if cpu_percent > 80:
                self.results.append({
                    "issue": f"High CPU usage: {cpu_percent}%",
                    "severity": "medium",
                    "category": "system_health",
                    "detected_at": datetime.datetime.utcnow().isoformat()
                })
            
            if memory.percent > 80:
                self.results.append({
                    "issue": f"High memory usage: {memory.percent}%",
                    "severity": "medium",
                    "category": "system_health",
                    "detected_at": datetime.datetime.utcnow().isoformat()
                })
            
            if disk.percent > 80:
                self.results.append({
                    "issue": f"Disk space is low: {disk.percent}% used",
                    "severity": "medium",
                    "category": "system_health",
                    "detected_at": datetime.datetime.utcnow().isoformat()
                })
            
            # Create health report
            health_report = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            logger.info(f"System health: CPU {cpu_percent}%, Memory {memory.percent}%, Disk {disk.percent}%")
            return health_report
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            self.results.append({
                "issue": f"Error checking system health: {str(e)}",
                "severity": "high",
                "category": "diagnostics_error",
                "detected_at": datetime.datetime.utcnow().isoformat()
            })
            return {"error": str(e)}
    
    def check_module_dependencies(self) -> List[Dict[str, Any]]:
        """
        Check module dependencies and imports.
        
        Returns:
            List of dependency issues
        """
        logger.info("Checking module dependencies")
        issues = []
        
        for root, _, files in os.walk("."):
            # Skip directories that are likely to contain external code
            if any(skip_dir in root for skip_dir in [".git", "__pycache__", "venv", ".venv", "node_modules"]):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    module_name = os.path.splitext(os.path.basename(path))[0]
                    
                    try:
                        # Check for import-related issues without actually importing
                        if '/' in path:
                            with open(path, 'r', errors='ignore') as f:
                                content = f.read()
                                
                            # Look for import statements
                            import_lines = [line.strip() for line in content.split('\n') 
                                          if line.strip().startswith(('import ', 'from '))]
                            
                            if import_lines:
                                try:
                                    # Just compile to check for syntax errors
                                    compile(content, path, 'exec')
                                except SyntaxError as e:
                                    issues.append({
                                        "file": path,
                                        "issue": f"Syntax error: {str(e)}",
                                        "severity": "high",
                                        "category": "dependencies",
                                        "detected_at": datetime.datetime.utcnow().isoformat()
                                    })
                    except Exception as e:
                        # Skip import errors, as they're expected during testing
                        pass
        
        # Add issues to results
        self.results.extend(issues)
        logger.info(f"Found {len(issues)} dependency issues")
        return issues
    
    def save_diagnostics(self) -> bool:
        """
        Save diagnostic results to file.
        
        Returns:
            bool: True if the results were saved successfully
        """
        try:
            with open(self.diagnostics_path, 'w') as f:
                json.dump(self.results, f, indent=4)
            logger.info(f"Saved {len(self.results)} diagnostic results to {self.diagnostics_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving diagnostics: {e}")
            return False
    
    def _count_by_severity(self) -> Dict[str, int]:
        """
        Count issues by severity.
        
        Returns:
            Dict with counts by severity
        """
        counts = {"high": 0, "medium": 0, "low": 0}
        for issue in self.results:
            severity = issue.get("severity", "low")
            counts[severity] = counts.get(severity, 0) + 1
        return counts


def run_standalone_diagnosis():
    """Run a standalone diagnosis from the command line."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    diagnostics = DiagnosticsModule()
    diagnostics._initialize()
    results = diagnostics.run_full_diagnosis()
    
    print(f"Diagnosis completed at {results['timestamp']}")
    print(f"Found {results['total_issues']} issues:")
    print(f"  High: {results['severity_counts'].get('high', 0)}")
    print(f"  Medium: {results['severity_counts'].get('medium', 0)}")
    print(f"  Low: {results['severity_counts'].get('low', 0)}")
    print(f"Results saved to {diagnostics.diagnostics_path}")


if __name__ == "__main__":
    run_standalone_diagnosis()

import os
import json
from datetime import datetime

def scan_directory(directory):
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', errors='ignore') as f:
                    content = f.read()
                    if 'TODO' in content or 'pass' in content:
                        results.append({
                            "file": path,
                            "issue": "Contains TODO/pass placeholder",
                            "severity": "low",
                            "detected_at": datetime.utcnow().isoformat()
                        })
    return results

def save_diagnosis(results):
    log_path = "reflex_diagnosis_log.json"
    with open(log_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Diagnosis completed. {len(results)} issues logged.")

if __name__ == "__main__":
    scan_results = scan_directory(".")
    save_diagnosis(scan_results)

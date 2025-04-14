#!/usr/bin/env python3
"""
SARYA Web Interface
Flask application that provides a web interface for the SARYA system.
"""
import os
import json
import threading
import time
import signal
import traceback
from flask import render_template, request, jsonify, redirect, url_for
from app import app, db
from models import Clone, Metric, ReflexLog, Plugin, SystemConfig, DiagnosticResult, Tool
from sarya import SaryaSystem

# Initialize SARYA
sarya = SaryaSystem()
config_path = os.path.join(os.path.dirname(__file__), "sarya_config.json")
sarya_initialized = sarya.initialize(config_path)
sarya_thread = None

# Make sure the config has redis disabled
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    if 'redis' not in config or config['redis'].get('enabled', True):
        config['redis'] = {'enabled': False}
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
except Exception as e:
    print(f"Error updating config: {e}")

@app.route('/')
def index():
    """Home page"""
    status = "Running" if sarya_thread and sarya_thread.is_alive() else "Stopped"
    
    # Get the system status
    system_info = {
        "status": status,
        "initialized": sarya_initialized,
        "config_path": config_path,
        "modules": []
    }
    
    return render_template('index.html', system_info=system_info)

@app.route('/start', methods=['POST'])
def start_sarya():
    """Start the SARYA system"""
    global sarya_thread
    
    if sarya_thread and sarya_thread.is_alive():
        return jsonify({"status": "SARYA is already running"})
    
    # Reset the signals for the main thread
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    def run_sarya():
        """Run SARYA in a separate thread"""
        try:
            sarya.start()
            sarya.run()
        except Exception as e:
            print(f"Error in SARYA thread: {e}")
    
    sarya_thread = threading.Thread(target=run_sarya)
    sarya_thread.daemon = True
    sarya_thread.start()
    
    # Wait a bit for it to start
    time.sleep(1)
    
    return jsonify({"status": "SARYA started successfully"})

@app.route('/stop', methods=['POST'])
def stop_sarya():
    """Stop the SARYA system"""
    if not sarya_thread or not sarya_thread.is_alive():
        return jsonify({"status": "SARYA is not running"})
    
    sarya.stop()
    sarya_thread.join(timeout=5)
    
    if sarya_thread.is_alive():
        return jsonify({"status": "Failed to stop SARYA"})
    
    return jsonify({"status": "SARYA stopped successfully"})

@app.route('/status')
def status():
    """Get the current status of the SARYA system"""
    status = "Running" if sarya_thread and sarya_thread.is_alive() else "Stopped"
    
    # Get clone queue information
    from clone_system.clone_queue import clone_queue
    
    try:
        queue_info = {
            "queue_size": clone_queue.get_queue_size(),
            "processing_size": clone_queue.get_processing_size(),
            "queued_clones": clone_queue.get_queued_clones(),
            "processing_clones": clone_queue.get_processing_clones()
        }
    except Exception as e:
        queue_info = {
            "error": str(e),
            "queue_size": 0,
            "processing_size": 0,
            "queued_clones": [],
            "processing_clones": []
        }
    
    return jsonify({
        "status": status,
        "initialized": sarya_initialized,
        "queue_info": queue_info
    })

@app.route('/config')
def get_config():
    """Get the current configuration"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)})

# Database routes
@app.route('/clones')
def get_clones():
    """Get all clones from the database"""
    try:
        clones = Clone.query.all()
        return jsonify([clone.to_dict() for clone in clones])
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/diagnostics')
def get_diagnostics():
    """Get all diagnostic results from the database"""
    try:
        diagnostics = DiagnosticResult.query.order_by(DiagnosticResult.created_at.desc()).limit(100).all()
        return jsonify([d.to_dict() for d in diagnostics])
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/diagnostics/run', methods=['POST'])
def run_diagnostics():
    """Run system diagnostics"""
    try:
        from core.diagnostics import DiagnosticsModule
        
        # Create diagnostics module
        diagnostics = DiagnosticsModule()
        diagnostics._initialize()
        
        # Run diagnostics
        results = diagnostics.run_full_diagnosis()
        
        # Save results to database
        for issue in diagnostics.results:
            diagnostic = DiagnosticResult(
                issue=issue.get('issue', 'Unknown issue'),
                file=issue.get('file'),
                severity=issue.get('severity', 'low'),
                category=issue.get('category', 'general'),
                details=json.dumps(issue),
                is_resolved=False
            )
            db.session.add(diagnostic)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Diagnostics completed, found {results.get('total_issues', 0)} issues",
            "results": results
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})
        
@app.route('/tools')
def get_tools():
    """Get all tools from the database"""
    try:
        tools = Tool.query.all()
        return jsonify([tool.to_dict() for tool in tools])
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/tools/sync', methods=['POST'])
def sync_tools():
    """Sync tools from registry to database"""
    try:
        from core.tools_registry import ToolsRegistry
        
        # Create tools registry
        registry = ToolsRegistry()
        registry._initialize()
        
        # Get all tools from registry
        tools_dict = registry.get_all_tools()
        
        # Sync with database
        for name, tool_data in tools_dict.items():
            # Check if tool exists
            tool = Tool.query.filter_by(name=name).first()
            
            if tool:
                # Update existing tool
                tool.tool_type = tool_data.get('type', 'unknown')
                tool.access_method = tool_data.get('access_method', 'unknown')
                tool.capabilities = tool_data.get('capabilities', [])
                tool.config = tool_data
                tool.status = tool_data.get('status', 'disabled')
            else:
                # Create new tool
                tool = Tool(
                    name=name,
                    tool_type=tool_data.get('type', 'unknown'),
                    access_method=tool_data.get('access_method', 'unknown'),
                    capabilities=tool_data.get('capabilities', []),
                    config=tool_data,
                    status=tool_data.get('status', 'disabled')
                )
                db.session.add(tool)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Synced {len(tools_dict)} tools with database"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

@app.route('/clones/<clone_id>')
def get_clone(clone_id):
    """Get a specific clone from the database"""
    try:
        clone = Clone.query.get(clone_id)
        if clone:
            return jsonify(clone.to_dict())
        else:
            return jsonify({"error": "Clone not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/clones/<clone_id>', methods=['DELETE'])
def delete_clone(clone_id):
    """Delete a clone from the database"""
    try:
        clone = Clone.query.get(clone_id)
        if clone:
            db.session.delete(clone)
            db.session.commit()
            return jsonify({"status": f"Clone {clone_id} deleted successfully"})
        else:
            return jsonify({"error": "Clone not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)})

@app.route('/metrics')
def get_metrics():
    """Get all metrics from the database"""
    try:
        metrics = Metric.query.order_by(Metric.timestamp.desc()).limit(100).all()
        return jsonify([metric.to_dict() for metric in metrics])
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/reflex_logs')
def get_reflex_logs():
    """Get all reflex logs from the database"""
    try:
        reflex_logs = ReflexLog.query.order_by(ReflexLog.created_at.desc()).limit(100).all()
        return jsonify([log.to_dict() for log in reflex_logs])
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/intelligence/knowledge')
def get_knowledge():
    """Get knowledge base concepts"""
    try:
        from sarya import intelligence_module
        
        # Get all concepts from knowledge base
        if "concepts" in intelligence_module.knowledge_base:
            concepts = intelligence_module.knowledge_base["concepts"]
            return jsonify(concepts)
        else:
            return jsonify({})
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/intelligence/add_knowledge', methods=['POST'])
def add_knowledge():
    """Add knowledge to the knowledge base"""
    try:
        from sarya import intelligence_module
        
        data = request.json
        concept_id = data.get('concept_id')
        concept_data = {
            "name": data.get('name'),
            "description": data.get('description'),
            "tags": data.get('tags', [])
        }
        
        # Add to knowledge base
        success = intelligence_module.add_knowledge(concept_id, concept_data)
        
        if success:
            return jsonify({"status": "success", "message": f"Added concept {concept_id}"})
        else:
            return jsonify({"status": "error", "message": "Failed to add concept"})
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/intelligence/reason', methods=['POST'])
def reason():
    """Apply reasoning to a query"""
    try:
        from sarya import intelligence_module
        
        data = request.json
        reasoning_type = data.get('reasoning_type', 'deductive')
        query = data.get('query', {})
        
        # Apply reasoning
        result = intelligence_module.reason(query, reasoning_type)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/intelligence/decisions')
def get_decisions():
    """Get decision history"""
    try:
        from sarya import intelligence_module
        
        # Get decision history
        decisions = intelligence_module.get_decision_history()
        
        return jsonify(decisions)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/plugins')
def get_plugins():
    """Get all plugins from the database"""
    try:
        plugins = Plugin.query.all()
        return jsonify([plugin.to_dict() for plugin in plugins])
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/system_config')
def get_system_configs():
    """Get all system configs from the database"""
    try:
        configs = SystemConfig.query.all()
        return jsonify([config.to_dict() for config in configs])
    except Exception as e:
        return jsonify({"error": str(e)})

@app.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create basic templates if they don't exist
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SARYA - AI Intelligence Framework</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1>SARYA - AI Intelligence Framework</h1>
        
        <ul class="nav nav-tabs mb-4" id="mainTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="status-tab" data-bs-toggle="tab" data-bs-target="#status" type="button" role="tab" aria-controls="status" aria-selected="true">Status</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="intelligence-tab" data-bs-toggle="tab" data-bs-target="#intelligence" type="button" role="tab" aria-controls="intelligence" aria-selected="false">Intelligence</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="clones-tab" data-bs-toggle="tab" data-bs-target="#clones" type="button" role="tab" aria-controls="clones" aria-selected="false">Clones</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="diagnostics-tab" data-bs-toggle="tab" data-bs-target="#diagnostics" type="button" role="tab" aria-controls="diagnostics" aria-selected="false">Diagnostics</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="tools-tab" data-bs-toggle="tab" data-bs-target="#tools" type="button" role="tab" aria-controls="tools" aria-selected="false">Tools</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="logs-tab" data-bs-toggle="tab" data-bs-target="#logs" type="button" role="tab" aria-controls="logs" aria-selected="false">Logs</button>
            </li>
        </ul>
        
        <div class="tab-content" id="mainTabContent">
            <!-- Status Tab -->
            <div class="tab-pane fade show active" id="status" role="tabpanel" aria-labelledby="status-tab">
                <div class="card mb-4">
                    <div class="card-header">
                        System Status
                    </div>
                    <div class="card-body">
                        <p><strong>Status:</strong> {{ system_info.status }}</p>
                        <p><strong>Initialized:</strong> {{ system_info.initialized }}</p>
                        <p><strong>Config Path:</strong> {{ system_info.config_path }}</p>
                        <div class="mb-3">
                            <button id="startBtn" class="btn btn-success">Start SARYA</button>
                            <button id="stopBtn" class="btn btn-danger">Stop SARYA</button>
                        </div>
                        <div id="statusMessage" class="alert alert-info d-none"></div>
                    </div>
                </div>
            </div>
            
            <!-- Intelligence Tab -->
            <div class="tab-pane fade" id="intelligence" role="tabpanel" aria-labelledby="intelligence-tab">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Intelligence Module</span>
                        <button id="refreshIntelligence" class="btn btn-sm btn-secondary">Refresh</button>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header">Knowledge Base</div>
                                    <div class="card-body">
                                        <h5>Core Concepts</h5>
                                        <div id="knowledgeList" class="list-group mb-3">
                                            <div class="list-group-item">Loading...</div>
                                        </div>
                                        
                                        <h5>Add Knowledge</h5>
                                        <form id="addKnowledgeForm" class="mt-2">
                                            <div class="mb-2">
                                                <label for="conceptId" class="form-label">Concept ID</label>
                                                <input type="text" class="form-control" id="conceptId" required>
                                            </div>
                                            <div class="mb-2">
                                                <label for="conceptName" class="form-label">Name</label>
                                                <input type="text" class="form-control" id="conceptName" required>
                                            </div>
                                            <div class="mb-2">
                                                <label for="conceptDescription" class="form-label">Description</label>
                                                <textarea class="form-control" id="conceptDescription" rows="2" required></textarea>
                                            </div>
                                            <div class="mb-2">
                                                <label for="conceptTags" class="form-label">Tags (comma separated)</label>
                                                <input type="text" class="form-control" id="conceptTags">
                                            </div>
                                            <button type="submit" class="btn btn-primary btn-sm">Add Concept</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header">Reasoning</div>
                                    <div class="card-body">
                                        <h5>Test Reasoning</h5>
                                        <form id="reasoningForm" class="mt-2">
                                            <div class="mb-2">
                                                <label for="reasoningType" class="form-label">Reasoning Type</label>
                                                <select class="form-select" id="reasoningType" required>
                                                    <option value="deductive">Deductive (General to Specific)</option>
                                                    <option value="inductive">Inductive (Specific to General)</option>
                                                    <option value="abductive">Abductive (Best Explanation)</option>
                                                    <option value="analogical">Analogical (Source to Target)</option>
                                                </select>
                                            </div>
                                            <div class="mb-2">
                                                <label for="reasoningQuery" class="form-label">Query (JSON)</label>
                                                <textarea class="form-control" id="reasoningQuery" rows="5" required>{"premises": ["All humans are mortal", "Socrates is human"], "conclusion": "Socrates is mortal"}</textarea>
                                            </div>
                                            <button type="submit" class="btn btn-primary btn-sm">Execute Reasoning</button>
                                        </form>
                                        
                                        <div class="mt-3">
                                            <h5>Result</h5>
                                            <pre id="reasoningResult" class="p-2 bg-dark text-light rounded" style="max-height: 200px; overflow-y: auto;">Submit a query to see results</pre>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="card">
                                    <div class="card-header">Decision History</div>
                                    <div class="card-body">
                                        <div id="decisionHistory" class="list-group">
                                            <div class="list-group-item">No decisions yet</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Clones Tab -->
            <div class="tab-pane fade" id="clones" role="tabpanel" aria-labelledby="clones-tab">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Clones</span>
                        <button id="refreshClones" class="btn btn-sm btn-secondary">Refresh</button>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>Status</th>
                                        <th>Progress</th>
                                        <th>Created</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="clonesTable">
                                    <tr>
                                        <td colspan="7" class="text-center">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Diagnostics Tab -->
            <div class="tab-pane fade" id="diagnostics" role="tabpanel" aria-labelledby="diagnostics-tab">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>System Diagnostics</span>
                        <div>
                            <button id="runDiagnostics" class="btn btn-sm btn-primary">Run Diagnostics</button>
                            <button id="refreshDiagnostics" class="btn btn-sm btn-secondary ms-2">Refresh</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="diagnosticsResults">
                            <div class="alert alert-info">Click "Run Diagnostics" to analyze the system's health.</div>
                        </div>
                        <div class="table-responsive mt-3">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Issue</th>
                                        <th>File</th>
                                        <th>Severity</th>
                                        <th>Category</th>
                                        <th>Created</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="diagnosticsTable">
                                    <tr>
                                        <td colspan="6" class="text-center">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Tools Tab -->
            <div class="tab-pane fade" id="tools" role="tabpanel" aria-labelledby="tools-tab">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Tools Registry</span>
                        <div>
                            <button id="syncTools" class="btn btn-sm btn-primary">Sync Tools</button>
                            <button id="refreshTools" class="btn btn-sm btn-secondary ms-2">Refresh</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="toolsResults">
                            <div class="alert alert-info">Click "Sync Tools" to update tools from the registry.</div>
                        </div>
                        <div class="table-responsive mt-3">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>Access Method</th>
                                        <th>Status</th>
                                        <th>Updated</th>
                                    </tr>
                                </thead>
                                <tbody id="toolsTable">
                                    <tr>
                                        <td colspan="5" class="text-center">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Logs Tab -->
            <div class="tab-pane fade" id="logs" role="tabpanel" aria-labelledby="logs-tab">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Reflex Logs</span>
                        <button id="refreshLogs" class="btn btn-sm btn-secondary">Refresh</button>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Type</th>
                                        <th>Trigger</th>
                                        <th>Response</th>
                                        <th>Intensity</th>
                                        <th>Created</th>
                                    </tr>
                                </thead>
                                <tbody id="logsTable">
                                    <tr>
                                        <td colspan="5" class="text-center">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // System Status Tab
        document.getElementById('startBtn').addEventListener('click', function() {
            fetch('/start', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                const statusMsg = document.getElementById('statusMessage');
                statusMsg.textContent = data.status;
                statusMsg.classList.remove('d-none');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            });
        });
        
        document.getElementById('stopBtn').addEventListener('click', function() {
            fetch('/stop', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                const statusMsg = document.getElementById('statusMessage');
                statusMsg.textContent = data.status;
                statusMsg.classList.remove('d-none');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            });
        });
        
        // Clones Tab
        function loadClones() {
            fetch('/clones')
            .then(response => response.json())
            .then(clones => {
                const table = document.getElementById('clonesTable');
                if (clones.length === 0) {
                    table.innerHTML = '<tr><td colspan="7" class="text-center">No clones found</td></tr>';
                    return;
                }
                
                table.innerHTML = '';
                clones.forEach(clone => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${clone.id}</td>
                        <td>${clone.name}</td>
                        <td>${clone.clone_type}</td>
                        <td>${clone.status}</td>
                        <td>${(clone.progress * 100).toFixed(1)}%</td>
                        <td>${new Date(clone.created_at).toLocaleString()}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="deleteClone('${clone.id}')">Delete</button>
                        </td>
                    `;
                    table.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('Error loading clones:', error);
                document.getElementById('clonesTable').innerHTML = 
                    '<tr><td colspan="7" class="text-center text-danger">Error loading clones</td></tr>';
            });
        }
        
        function deleteClone(id) {
            if (confirm('Are you sure you want to delete this clone?')) {
                fetch('/clones/' + id, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.status || data.error);
                    loadClones();
                })
                .catch(error => {
                    console.error('Error deleting clone:', error);
                    alert('Error deleting clone');
                });
            }
        }
        
        document.getElementById('refreshClones').addEventListener('click', loadClones);
        
        // Diagnostics Tab
        function loadDiagnostics() {
            fetch('/diagnostics')
            .then(response => response.json())
            .then(diagnostics => {
                const table = document.getElementById('diagnosticsTable');
                if (diagnostics.length === 0) {
                    table.innerHTML = '<tr><td colspan="6" class="text-center">No diagnostic results found</td></tr>';
                    return;
                }
                
                table.innerHTML = '';
                diagnostics.forEach(diagnostic => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${diagnostic.issue}</td>
                        <td>${diagnostic.file || 'N/A'}</td>
                        <td><span class="badge ${getSeverityClass(diagnostic.severity)}">${diagnostic.severity}</span></td>
                        <td>${diagnostic.category}</td>
                        <td>${new Date(diagnostic.created_at).toLocaleString()}</td>
                        <td>${diagnostic.is_resolved ? 'Resolved' : 'Open'}</td>
                    `;
                    table.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('Error loading diagnostics:', error);
                document.getElementById('diagnosticsTable').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-danger">Error loading diagnostics</td></tr>';
            });
        }
        
        function getSeverityClass(severity) {
            switch(severity) {
                case 'high': return 'bg-danger';
                case 'medium': return 'bg-warning';
                case 'low': return 'bg-info';
                default: return 'bg-secondary';
            }
        }
        
        document.getElementById('runDiagnostics').addEventListener('click', function() {
            const resultsDiv = document.getElementById('diagnosticsResults');
            resultsDiv.innerHTML = '<div class="alert alert-info">Running diagnostics, please wait...</div>';
            
            fetch('/diagnostics/run', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    return;
                }
                
                resultsDiv.innerHTML = `
                    <div class="alert alert-success">
                        ${data.message}
                        <div class="mt-2">
                            <strong>Issues by severity:</strong>
                            <span class="badge bg-danger ms-2">High: ${data.results.severity_counts.high || 0}</span>
                            <span class="badge bg-warning ms-2">Medium: ${data.results.severity_counts.medium || 0}</span>
                            <span class="badge bg-info ms-2">Low: ${data.results.severity_counts.low || 0}</span>
                        </div>
                    </div>
                `;
                
                loadDiagnostics();
            })
            .catch(error => {
                console.error('Error running diagnostics:', error);
                resultsDiv.innerHTML = '<div class="alert alert-danger">Error running diagnostics</div>';
            });
        });
        
        document.getElementById('refreshDiagnostics').addEventListener('click', loadDiagnostics);
        
        // Tools Tab
        function loadTools() {
            fetch('/tools')
            .then(response => response.json())
            .then(tools => {
                const table = document.getElementById('toolsTable');
                if (tools.length === 0) {
                    table.innerHTML = '<tr><td colspan="5" class="text-center">No tools found</td></tr>';
                    return;
                }
                
                table.innerHTML = '';
                tools.forEach(tool => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${tool.name}</td>
                        <td>${tool.tool_type}</td>
                        <td>${tool.access_method}</td>
                        <td><span class="badge ${tool.status === 'enabled' ? 'bg-success' : 'bg-secondary'}">${tool.status}</span></td>
                        <td>${new Date(tool.updated_at).toLocaleString()}</td>
                    `;
                    table.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('Error loading tools:', error);
                document.getElementById('toolsTable').innerHTML = 
                    '<tr><td colspan="5" class="text-center text-danger">Error loading tools</td></tr>';
            });
        }
        
        document.getElementById('syncTools').addEventListener('click', function() {
            const resultsDiv = document.getElementById('toolsResults');
            resultsDiv.innerHTML = '<div class="alert alert-info">Syncing tools, please wait...</div>';
            
            fetch('/tools/sync', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    return;
                }
                
                resultsDiv.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                loadTools();
            })
            .catch(error => {
                console.error('Error syncing tools:', error);
                resultsDiv.innerHTML = '<div class="alert alert-danger">Error syncing tools</div>';
            });
        });
        
        document.getElementById('refreshTools').addEventListener('click', loadTools);
        
        // Logs Tab
        function loadLogs() {
            fetch('/reflex_logs')
            .then(response => response.json())
            .then(logs => {
                const table = document.getElementById('logsTable');
                if (logs.length === 0) {
                    table.innerHTML = '<tr><td colspan="5" class="text-center">No logs found</td></tr>';
                    return;
                }
                
                table.innerHTML = '';
                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${log.reflex_type}</td>
                        <td>${log.trigger}</td>
                        <td>${log.response}</td>
                        <td>${log.intensity.toFixed(2)}</td>
                        <td>${new Date(log.created_at).toLocaleString()}</td>
                    `;
                    table.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('Error loading logs:', error);
                document.getElementById('logsTable').innerHTML = 
                    '<tr><td colspan="5" class="text-center text-danger">Error loading logs</td></tr>';
            });
        }
        
        document.getElementById('refreshLogs').addEventListener('click', loadLogs);
        
        // Initialize tabs
        document.addEventListener('DOMContentLoaded', function() {
            // Load initial data
            loadClones();
            loadDiagnostics();
            loadTools();
            loadLogs();
            
            // Add tab switching event listeners
            document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
                tab.addEventListener('shown.bs.tab', function(event) {
                    const targetId = event.target.getAttribute('aria-controls');
                    switch(targetId) {
                        case 'clones':
                            loadClones();
                            break;
                        case 'diagnostics':
                            loadDiagnostics();
                            break;
                        case 'tools':
                            loadTools();
                            break;
                        case 'logs':
                            loadLogs();
                            break;
                    }
                });
            });
        });
        
        // Make deleteClone available globally
        window.deleteClone = deleteClone;
    </script>
</body>
</html>""")
    
    # Handle shutting down SARYA when the Flask app exits
    def signal_handler(sig, frame):
        print('Shutting down SARYA...')
        if sarya_thread and sarya_thread.is_alive():
            sarya.stop()
            sarya_thread.join(timeout=5)
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)
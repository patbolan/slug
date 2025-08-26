from flask import Blueprint, render_template, abort, redirect, url_for

from tools.utils import execute_module_tool
#from tools.process_manager import ProcessManager
from tools.process_module_manager import ProcessModuleManager
from utils import get_process_file_path, get_file_tree, get_study_path



tools_bp = Blueprint('tools_bp', __name__)

# Tool commands. Supports study-level, subject-level, and project-level tools.
@tools_bp.route('/tools/<tool_name>/<command>/', methods=['POST'])
@tools_bp.route('/tools/<tool_name>/<command>/subjects/<subject_name>/', methods=['POST'])
@tools_bp.route('/tools/<tool_name>/<command>/subjects/<subject_name>/studies/<study_name>/', methods=['POST'])
def tool_command(tool_name, command, subject_name=None, study_name=None):

    print(f"Tool: {tool_name}, Command: {command}, Subject: {subject_name}, Study: {study_name}")
    #execute_tool(tool_name, command, subject_name, study_name)
    execute_module_tool(tool_name, command, subject_name, study_name)
    return f"Tool '{tool_name}' executed command '{command}' for subject '{subject_name}' and study '{study_name}'.", 200




@tools_bp.route('/processes')
def processes():
    # Create an instance of ProcessManager
    process_manager = ProcessModuleManager()

    # Get the list of running and completed processes
    running_processes = process_manager.get_processes(folder_type='running')
    completed_processes = process_manager.get_processes(folder_type='completed')

    # Render the processes.html template with both lists
    return render_template('processes.html', 
                           running_processes=running_processes, 
                           completed_processes=completed_processes)

@tools_bp.route('/process/<pid>')
def process_info(pid):
    # Create an instance of ProcessManager
    process_manager = ProcessModuleManager()

    # Get process information
    process_info = process_manager.get_process_info(pid)

    # Generate file tree
    file_tree = get_file_tree(get_process_file_path(pid))

    # If the process does not exist, return a 404 error
    if not process_info:
        abort(404, description=f"Process with PID {pid} not found.")

    return render_template('process.html', 
                           process_info=process_info, 
                           file_tree=file_tree)

@tools_bp.route('/clear-running-logs', methods=['POST'])
def clear_running_logs():
    pm = ProcessModuleManager()
    pm.clear_logs(folder_type='runing')

    return redirect(url_for('tools_bp.processes'))

@tools_bp.route('/clear-completed-logs', methods=['POST'])
def clear_completed_logs():
    pm = ProcessModuleManager()
    pm.clear_logs(folder_type='completed')

    return redirect(url_for('tools_bp.processes'))
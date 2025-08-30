from flask import Blueprint, render_template, abort, redirect, url_for, request, current_app

from tools.utils import execute_module_tool_simply
#from tools.process_manager import ProcessManager
from tools.process_module_manager import ProcessModuleManager
from utils import get_process_file_path, get_file_tree, get_study_path



tools_bp = Blueprint('tools_bp', __name__)

# Tool commands. Supports study-level, subject-level, and project-level tools.
@tools_bp.route('/tools/<tool_name>/<command>/', methods=['POST'])
@tools_bp.route('/tools/<tool_name>/<command>/subjects/<subject_name>/', methods=['POST'])
@tools_bp.route('/tools/<tool_name>/<command>/subjects/<subject_name>/studies/<study_name>/', methods=['POST'])
def tool_command(tool_name, command, subject_name=None, study_name=None):

    # Calculate the target paths
    if subject_name and study_name:
        target_path = get_study_path(subject_name, study_name)
    elif subject_name:
        target_path = get_study_path(subject_name)
    else:   
        target_path = None # Should be project, at some point.

    # Print the basic tool information
    current_app.logger.debug(f"Tool: {tool_name}, Command: {command}, Subject: {subject_name}, Study: {study_name}, target_path: {target_path}")

    # Check for options in the query parameters
    options = request.args.to_dict()

    # Execute the tool command
    execute_module_tool_simply(tool_name, command, subject_name, study_name, target_path, options)

    return f"Tool '{tool_name}' executed command '{command}' for target path '{target_path}' and options '{options}'.", 200


@tools_bp.route('/processes')
def processes():
    # Create an instance of ProcessManager
    process_manager = ProcessModuleManager()

    # Get the list of running and completed processes
    running_processes = process_manager.get_process_dicts(folder_type='running')
    completed_processes = process_manager.get_process_dicts(folder_type='completed')

    # Render the processes.html template with both lists
    return render_template('processes.html', 
                           running_processes=running_processes, 
                           completed_processes=completed_processes)

@tools_bp.route('/process/<pid>')
def process_info(pid):
    # Create an instance of ProcessManager
    process_manager = ProcessModuleManager()

    # Get process information
    process_info = process_manager.get_process_dict(pid)
    current_app.logger.debug(f"Process info for PID {pid}: {process_info}")

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
    pm.clear_logs(folder_type='running')

    return redirect(url_for('tools_bp.processes'))

@tools_bp.route('/clear-completed-logs', methods=['POST'])
def clear_completed_logs():
    pm = ProcessModuleManager()
    pm.clear_logs(folder_type='completed')

    return redirect(url_for('tools_bp.processes'))
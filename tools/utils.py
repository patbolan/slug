from flask import current_app
from utils import get_subject_type, get_study_type, get_module_folder, get_study_path
from tools.module_wrapper import ModuleWrapper
from tools.process_module_manager import ProcessModuleManager
import os

def get_module_configuration_for_study(subject_name, study_name):
    """
    Returns the module configuration for a given study based on its type.
    The configuration is expected to be in a JSON file named 'study_<study_type>.json'
    located in the module folder.
    """
    study_type = get_study_type(subject_name, study_name)
    json_config_path = os.path.join(get_module_folder(), f'study_{study_type}.json')

    if os.path.isfile(json_config_path):
        import json
        with open(json_config_path, 'r') as f:
            module_configuration = json.load(f)
        return module_configuration
    else:
        current_app.logger.error(f'Module configuration not found: {json_config_path}')
        return None
    

def get_tool_menu_for_study(subject_name, study_name):
    """
    The processing tools are determined by the module_configuration.json
    Wait... TBD

    This returns a tool menu, a list of tools suitable for this study,
    A single tool is a menu item.
    each menu item is a dictionary with values needed by the web interface
    """
    module_configuration = get_module_configuration_for_study(subject_name, study_name)
    if module_configuration is None:
        return None

    tool_menu = []
    for module_name in module_configuration:

        # Great. Here is where you instantiate this object, get its status dict.
        # Append status dict to toolset
        wrapper = get_module_wrapper(module_name)
        status = wrapper.get_status_for_study(subject_name, study_name)

        # Check values from dicts, make sure they are there
        status_string = status.get("state", "unknown")
        rationale_string = status.get("rationale", "")

        if status["state"] == "runnable":
            command = "run"
        elif status["state"] == "completed":
            if wrapper.is_undoable():
                command = "undo"
            else:
                command = None
        else:
            command = None

        # Go find PID
        pm = ProcessModuleManager()
        pid = pm.get_process_id(subject_name, study_name, module_name)
        # Note that the command line "status" request doesn't know about how slug
        # manages running processes, it just looks at the files. So if the process 
        # is started and has started creating files, the status is unclear. But here,
        # I know the status if it's in the running folder. Overwrite.
        if pm.is_running(pid):
            status_string = "running"
            rationale_string = f"{module_name} is running"
            command = None



        # Cool. Now from status prepare a dict to give to the web interface.
        # Name, status, options, mesage, pid, commands 
        tool_menu_item = {
            'name': f'{module_name}', 
            'status': status_string,
            'message': rationale_string,
            'command': command,
            'options': [
                {"name": "mode", "choices": ["nlls", "loglin", "cnn"], }, 
                {"name": "execution", "choices": ["inline","queued"] }
            ],
            'pid': f'{pid}' if pid else '',
        }
        tool_menu.append(tool_menu_item)    

    return tool_menu


# TEMP Load everything up from disk. 
# Later, we will load all modules and properties at startup, and then pull them from a memory structure.
def get_module_wrapper(tool_name):
    """
    Looks up the module folder and script for a given tool name from the CSV file.
    Returns (module_folder, module_script) or (None, None) if not found.
    """
    import csv
    csv_path = os.path.join(get_module_folder(), 'module_definitions.csv')
    if os.path.isfile(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['name'] == tool_name:
                    # Now get a module wrapper
                    wrapper = ModuleWrapper(
                        module_name=tool_name,  
                        module_folder=row['folder'],
                        module_script=row['script'])
                    return wrapper

    current_app.logger.error(f"Module '{tool_name}' not found in module_definitions.csv")            
    return None   


# This is my new, simplified interface for executing a module tool.
def execute_module_tool_simply(tool_name, command, subject_name, study_name, target, options):
    current_app.logger.debug(f"execute_module_tool_simply: {tool_name}, command: {command}, target: {target}, options: {options}")

    module_wrapper = get_module_wrapper(tool_name)
    if module_wrapper is None:
        raise ValueError(f"Module wrapper not found for tool '{tool_name}'")

    command_list = [module_wrapper.script_path, command, '--target', target] # ADD OPTIONS
    context_dict = {
        'tool_name': tool_name,
        'command': command,
        'subject_name': subject_name,   
        'study_name': study_name,
        'target_path': target, 
        'options': options
    }
    
    pm = ProcessModuleManager()
    #pm.run_commandline(command_list, context_dict, blocking=False)
    pm.run_commandline(command_list, context_dict, blocking=True)
    
    return None


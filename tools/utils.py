from flask import current_app
from utils import get_subject_type, get_study_type, get_module_folder, get_study_path
from tools.module_wrapper import ModuleWrapper
from tools.process_module_manager import ProcessModuleManager
import os

def get_module_configuration(subject_name, study_name):
    """
    Returns the module configuration for a given study based on its type.
    The configuration is expected to be in a JSON file named 'study_<study_type>.json'
    located in the module folder.
    """
    # Different module-list files depending on context (project, subject, study) and types
    if subject_name is None:
        json_config_path = os.path.join(get_module_folder(), f'module-list_project.json')    
    elif study_name is None:
        # Subject-level tool
        subject_type = get_subject_type(subject_name)
        if subject_type is None:
            json_config_path = os.path.join(get_module_folder(), f'module-list_subject.json')
        else:
            json_config_path = os.path.join(get_module_folder(), f'module-list_subject_{subject_type}.json')    
    else:
        # Study-level tool
        study_type = get_study_type(subject_name, study_name)
        if study_type is None:
            json_config_path = os.path.join(get_module_folder(), f'module-list_study.json')
        else:
            json_config_path = os.path.join(get_module_folder(), f'module-list_study_{study_type}.json')


    if os.path.isfile(json_config_path):
        import json
        with open(json_config_path, 'r') as f:
            module_configuration = json.load(f)
        return module_configuration
    else:
        current_app.logger.error(f'Module configuration not found: {json_config_path}')
        return None
    


def get_tool_menu(subject_name, study_name):
    """
    The processing tools are determined by the module_configuration.json
    Wait... TBD

    This returns a tool menu, a list of tools suitable for this study,
    A single tool is a menu item.
    each menu item is a dictionary with values needed by the web interface
    """
    module_configuration = get_module_configuration(subject_name, study_name)
    if module_configuration is None:
        return None

    tool_menu = []
    for module_name in module_configuration:

        # Great. Here is where you instantiate this object, get its status dict.
        # Append status dict to toolset
        wrapper = get_module_wrapper(module_name)
        if not wrapper:
            raise ValueError(f"Module wrapper not found for tool '{module_name}'")
        status = wrapper.get_status(subject_name, study_name)

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
            'pid': f'{pid}' if pid else ''
        }

        # Execution mode. Always add this option, default to "in-process" unless specified
        # by the module configuration
        default_execution_mode = module_configuration.get(module_name, {}).get(command, {}).get('execution-mode', 'in-process') 
        execution_option = {"name": "execution", "choices": ["in-process","background"], "default": default_execution_mode }

        # Specify options if there are commands to run.
        # Options come from the command line "properties" call. Defaults can be provided on a 
        # per-command basis in the module_configuration
        if command:
            # Options are like: {'mode': {'values': ['size', 'tree', 'ls']}}
            options = wrapper.properties.get("options")
            if options: 
                tool_menu_item['options'] = []
                for option_name, option_info in options.items():
                    choices = option_info.get('values', []) 
                    default = module_configuration.get(module_name, {}).get(command, {}).get('option-defaults', {}).get(option_name, {})
                    tool_menu_item['options'].append({"name": option_name, "choices": choices, "default": default })
                tool_menu_item['options'].append(execution_option)  # Add execution option at the end
            else:   
                tool_menu_item['options'] = [execution_option]  # Only execution option

        # Finally, append this to the tool menu
        tool_menu.append(tool_menu_item)    

    return tool_menu


# Global cache for ModuleWrapper instances
_module_wrapper_cache = {}


def get_module_wrapper(tool_name):
    """
    Retrieves a cached ModuleWrapper instance for the given tool name.
    If the instance does not exist, it creates one and caches it.
    Instead you could just read the disk each time, but that is a bit slow.
    """
    global _module_wrapper_cache

    # Check if the tool_name is already in the cache
    if tool_name in _module_wrapper_cache:
        return _module_wrapper_cache[tool_name]

    # If not cached, create a new ModuleWrapper instance
    import csv
    csv_path = os.path.join(get_module_folder(), 'module_definitions.csv')
    if os.path.isfile(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['name'] == tool_name:
                    # Create and cache the ModuleWrapper instance
                    wrapper = ModuleWrapper(
                        module_name=tool_name,
                        module_folder=row['folder'],
                        module_script=row['script']
                    )
                    _module_wrapper_cache[tool_name] = wrapper
                    return wrapper

    # Log an error if the tool is not found
    current_app.logger.error(f"Module '{tool_name}' not found in module_definitions.csv")
    return None


# This is my new, simplified interface for executing a module tool.
def execute_module_commandline(tool_name, command, subject_name, study_name, target, options):
    current_app.logger.debug(f"execute_module_commandline: {tool_name}, command: {command}, target: {target}, options: {options}")

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

    # Execution mode: in-process or background
    if options.get('execution', 'in-process') == 'in-process':
        blocking = True
    else:
        blocking = False

    # Other options except execution should be added to the command_list
    for option_name, option_value in options.items():
        if option_name != 'execution':  # Skip execution mode, already handled
            command_list.append(f'--{option_name}')
            command_list.append(str(option_value))
            
    current_app.logger.debug(f"Executing command list: {' '.join(command_list)}")
    
    # Command line execution is managed with the ProcessModuleManager
    pm = ProcessModuleManager()
    pm.run_commandline(command_list, context_dict, blocking=blocking) 
    
    return None


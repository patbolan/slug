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
        print(f'Module configuration not found: {json_config_path}')
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
        module_folder = module_configuration[module_name]['folder']
        module_script = module_configuration[module_name]['script']
        print(f'{module_name}, {module_folder}, {module_script}')

        # Great. Here is where you instantiate this object, get its status dict.
        # Append status dict to toolset
        wrapper = ModuleWrapper(
            module_name=module_name,
            module_folder=module_folder,
            module_script=module_script)
        status = wrapper.get_status_for_study(subject_name, study_name)

        # For debugging
        # print(f'--- properties for {module_name} ---')
        # print(wrapper.properties)
        # print(f'--- status for {module_name} ---')
        # print(status)

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
        elif status["state"] == "running":
            command = None

        # TODO Go find PID
        pm = ProcessModuleManager()
        pid = pm.get_process_id(subject_name, study_name, module_name)


        # Cool. Now from status prepare a dict to give to the web interface.
        # Name, status, options, mesage, pid, commands 
        tool_menu_item = {
            'name': f'{module_name}', 
            'status': status_string,
            'message': rationale_string,
            'command': command,
            'options': [
                {"name": "mode", "values": ["nlls", "loglin", "cnn"], }, 
                {"name": "execution", "values": ["inline","queued"] }
            ],
            'pid': None,
        }
        print(tool_menu_item)
        tool_menu.append(tool_menu_item)    

    return tool_menu

    
# TODO needs options, better interface for --target
def execute_module_tool(tool_name, command, subject_name, study_name):

    print(f"Executing module tool: {tool_name}, command: {command}, subject: {subject_name}, study: {study_name}")

    module_configuration = get_module_configuration_for_study(subject_name, study_name)
    if module_configuration is None:
        raise ValueError(f"Module configuration not found for study {study_name} of subject {subject_name}")

    if tool_name not in module_configuration:
        raise ValueError(f"Unknown tool '{tool_name}' for study {study_name} of subject {subject_name}")    
    
    target_path = get_study_path(subject_name, study_name)
    module_folder = module_configuration[tool_name]['folder']
    module_script = module_configuration[tool_name]['script']   
    wrapper = ModuleWrapper(
        module_name=tool_name,
        module_folder=module_folder,
        module_script=module_script)    

    if command == 'run':
        #tool.run_in_subprocess()
        wrapper.run_command_line('run', target_path)
    elif command == 'undo':
        #tool.undo()
        wrapper.run_command_line('undo', target_path)
    else:
        raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")


    

### THESE are broken for now. Revisit later

# def get_tools_for_subject(subject_name):
#     """ 
#     Returns a list of tools suitable for a subject, each as a dictionary summarizing its current state
#     """
#     from .simple_subject_tool import SimpleSubjectTool
#     simple_subject_tool = SimpleSubjectTool(subject_name)

#     return [
#         simple_subject_tool.get_status_dict(),
#     ]

# def get_tools_for_project():
#     """ 
#     Returns a list of tools suitable for the whole project
#     """
#     from .simple_project_tool import SimpleProjectTool
#     simple_project_tool = SimpleProjectTool()

#     return [
#         simple_project_tool.get_status_dict(),
#     ]    
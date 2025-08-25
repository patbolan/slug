from utils import get_subject_type, get_study_type, get_module_folder
from tools.module_wrapper import ModuleWrapper
import os


def get_tool_menu_for_study(subject_name, study_name):
    """
    The processing tools are determined by the module_configuration.json
    Wait... TBD

    This returns a tool menu, a list of tools suitable for this study,
    A single tool is a menu item.
    each menu item is a dictionary with values needed by the web interface
    """

    # TEMP: Look for a configuration specficially for this study type. May redo this, load once
    subject_type = get_subject_type(subject_name)
    study_type = get_study_type(subject_name, study_name)
    json_config_path = os.path.join(get_module_folder(), f'study_{study_type}.json')

    if os.path.isfile(json_config_path):
        import json
        with open(json_config_path, 'r') as f:
            module_configuration = json.load(f)
        
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
            # Go find PID
            

            # Cool. Now from status prepare a dict to give to the web interface.
            # Name, status, options, mesage, pid, commands 
            tool_menu_item = {
                'name': f'module_name', 
                'status': status_string,
                'message': rationale_string,
                'command': 'run',
                'pid': None,
            }
            tool_menu.append(tool_menu_item)    
        return tool_menu

    else:   
        print(f'module configuration not found: {json_config_path}')
        return None
    

    """
    removing all this code. Keep it as comment for reference.
    
    from .simple_study_tool import SimpleStudyTool
    from .nii_converter import NiiConverter
    from .dicom_raw_storage_cleaner import DicomRawStorageCleaner
    from .autotagger import AutoTagger
    from .template_registration import TemplateRegistration
    from .reslice_mask import ResliceMask
    from .parse_dicom_folder import ParseDicomFolder
    from .run_fits import RunFits

    #simple_tool = SimpleStudyTool(subject_name, study_name)
    nii_converter = NiiConverter(subject_name, study_name)
    parse_dicom_folder = ParseDicomFolder(subject_name, study_name)
    #dicom_raw_storage_cleaner = DicomRawStorageCleaner(subject_name, study_name)
    autotagger = AutoTagger(subject_name, study_name)
    template_registration = TemplateRegistration(subject_name, study_name)
    reslice_mask = ResliceMask(subject_name, study_name)
    run_all_fits = RunFits(subject_name, study_name)    

    # Different tools for humans and phantoms
    if is_subject_human(subject_name):
        return [
            parse_dicom_folder.get_status_dict(),
            autotagger.get_status_dict(),
            nii_converter.get_status_dict(),
        ]
    else:
        return [
            parse_dicom_folder.get_status_dict(),
            autotagger.get_status_dict(),
            nii_converter.get_status_dict(),
            template_registration.get_status_dict(),
            reslice_mask.get_status_dict(),
            run_all_fits.get_status_dict(),
        ]
    """

def get_tools_for_subject(subject_name):
    """ 
    Returns a list of tools suitable for a subject, each as a dictionary summarizing its current state
    """
    from .simple_subject_tool import SimpleSubjectTool
    simple_subject_tool = SimpleSubjectTool(subject_name)

    return [
        simple_subject_tool.get_status_dict(),
    ]

def get_tools_for_project():
    """ 
    Returns a list of tools suitable for the whole project
    """
    from .simple_project_tool import SimpleProjectTool
    simple_project_tool = SimpleProjectTool()

    return [
        simple_project_tool.get_status_dict(),
    ]

def execute_tool(tool_name, command, subject_name=None, study_name=None):
    """
    Executes a tool command.
    Supports tools that at study level, subject level, or project level.
    If subject_name and study_name are provided, it will execute a study-level tool.
    If study_name is not provided, it will execute a subject-level tool.
    If neither is provided, it will execute a project-level tool.
    """
    from .simple_study_tool import SimpleStudyTool
    from .nii_converter import NiiConverter
    from .dicom_raw_storage_cleaner import DicomRawStorageCleaner
    from .autotagger import AutoTagger
    from .template_registration import TemplateRegistration
    from .reslice_mask import ResliceMask
    from .simple_subject_tool import SimpleSubjectTool
    from .simple_project_tool import SimpleProjectTool
    from .parse_dicom_folder import ParseDicomFolder  
    from .run_fits import RunFits  

    if tool_name == 'nii-converter':
        tool = NiiConverter(subject_name, study_name)
    elif tool_name == 'simple-study-tool':
        tool = SimpleStudyTool(subject_name, study_name)
    elif tool_name == 'dicom-raw-storage-cleaner':
        tool = DicomRawStorageCleaner(subject_name, study_name)
    elif tool_name == 'autotagger':
        tool = AutoTagger(subject_name, study_name)
    elif tool_name == 'template-registration':
        tool = TemplateRegistration(subject_name, study_name)
    elif tool_name == 'reslice-mask':
        tool = ResliceMask(subject_name, study_name)
    elif tool_name == 'simple-subject-tool':
        tool = SimpleSubjectTool(subject_name)
    elif tool_name == 'simple-project-tool':
        tool = SimpleProjectTool()
    elif tool_name == 'parse-dicom-folder':
        tool = ParseDicomFolder(subject_name, study_name)
    elif tool_name == 'run-all-fits':
        tool = RunFits(subject_name, study_name)
    else:
        raise ValueError(f"Unknown tool '{tool_name}'")

    if command == 'run':
        tool.run_in_subprocess()
    elif command == 'undo':
        tool.undo()
    else:
        raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")
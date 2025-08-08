from utils import is_subject_human


def get_tools_for_study(subject_name, study_name):
    """
    Returns a list of tools for a given study, each as a dictionary summarizing its current state
    """
    from .simple_study_tool import SimpleStudyTool
    from .nii_converter import NiiConverter
    from .dicom_raw_storage_cleaner import DicomRawStorageCleaner
    from .autotagger import AutoTagger
    from .template_registration import TemplateRegistration
    from .reslice_mask import ResliceMask
    from .parse_dicom_folder import ParseDicomFolder

    #simple_tool = SimpleStudyTool(subject_name, study_name)
    nii_converter = NiiConverter(subject_name, study_name)
    parse_dicom_folder = ParseDicomFolder(subject_name, study_name)
    #dicom_raw_storage_cleaner = DicomRawStorageCleaner(subject_name, study_name)
    autotagger = AutoTagger(subject_name, study_name)
    template_registration = TemplateRegistration(subject_name, study_name)
    reslice_mask = ResliceMask(subject_name, study_name)

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
        ]

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
    else:
        raise ValueError(f"Unknown tool '{tool_name}'")

    if command == 'run':
        tool.run_in_subprocess()
    elif command == 'undo':
        tool.undo()
    else:
        raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")
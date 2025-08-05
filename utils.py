import os
import re
import pydicom
from config import Config

# Utility functions to retrieve folder paths
def get_data_folder():
    config = Config()
    return config.get('data_folder', '/default/data/folder')

def get_process_root_folder():
    config = Config()
    return config.get('process_root_folder', '/default/process/root/folder')

def get_module_folder():
    config = Config()
    return config.get('module_folder', '/default/module/folder')

def get_all_subjects():
    pattern = re.compile(r'^[A-Z]{3}-\d{4}$')  # Pattern for XXX-0000  
    subjects = [d for d in os.listdir(get_data_folder()) if os.path.isdir(os.path.join(get_data_folder(), d)) and pattern.match(d)]
    subjects.sort()
    return subjects

def get_studies_for_subject(subject_name):
    subject_path = get_subject_path(subject_name)
    if not os.path.isdir(subject_path):
        return []
    pattern = re.compile(r'MR-\d{8}$')  # Pattern for MR-YYYYMMDD
    studies = [d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d)) and pattern.match(d)]
    studies.sort()
    return studies

def get_subject_path(subject_name):
    subject_path = os.path.join(get_data_folder(), subject_name)
    if not os.path.isdir(subject_path):
        return None
    return subject_path

def get_study_path(subject_name, study_name):
    subject_path = get_subject_path(subject_name)
    if not subject_path:
        return None
    study_path = os.path.join(subject_path, study_name)
    if not os.path.isdir(study_path):
        return None
    return study_path

def get_subject_file_path(subject_name, file_name):
    subject_path = get_subject_path(subject_name)
    file_path = os.path.join(subject_path, file_name)
    return file_path    

def get_study_file_path(subject_name, study_name, file_name):
    study_path = get_study_path(subject_name, study_name)
    file_path = os.path.join(study_path, file_name)
    return file_path

def get_study_files(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not study_path:
        return []
    files = []
    for file_name in sorted(os.listdir(study_path)):
        full_path = os.path.join(study_path, file_name)
        if file_name.startswith('.'):
            continue  # Skip files starting with a period
        if os.path.isfile(full_path):
            files.append({'name': file_name, 'full_path': full_path})
    return files

def get_process_file_path(process_id, file_relative_path=None):
    from tools.process_manager import ProcessManager

    pm = ProcessManager()
    process_info = pm.get_process_info(process_id)
    if process_info is None:
        return None
    else:
        if process_info['status'] == 'running':
            return_path = os.path.join(get_process_root_folder(), 'running', f'{process_id}')
        else: 
            return_path = os.path.join(get_process_root_folder(), 'completed', f'{process_id}')

    # Add file to path 
    if file_relative_path is not None:
        return_path = os.path.join(return_path, file_relative_path)
        
    return return_path


# Get some DICOM header information
def get_sample_dicom_header(subject_name, study_name, series_name=None):
    study_path = get_study_path(subject_name, study_name)
    if not study_path:
        return None
    dicom_path = os.path.join(study_path, 'dicom-original')
    if not os.path.isdir(dicom_path):
        return None
    
    if series_name is None:
        # Grab a dicom folder
        dicom_folders = [f for f in os.listdir(dicom_path) if f.startswith('MR-SE')]
        if not dicom_folders:
            return None

        # Look in the first folder
        sample_folder = os.path.join(dicom_path, dicom_folders[0])  # Sort to get a consistent sample
    else:
        sample_folder = os.path.join(dicom_path, series_name)
        if not os.path.isdir(sample_folder):
            return None

    dicom_files = [f for f in os.listdir(sample_folder) if f.lower().endswith('.dcm')]
    if not dicom_files:
        return None
    sample_file = os.path.join(sample_folder, dicom_files[0])
    try:
        dicom_data = pydicom.dcmread(sample_file)
        return dicom_data
    except Exception as e:
        print(f"Error reading DICOM file {sample_file}: {e}")
        return None
    

def get_file_tree(path):
    """
    Recursively generates a hierarchical file tree for the given path.
    :param path: Root directory path.
    :return: List representing the file tree.
    """
    tree = []
    for entry in sorted(os.listdir(path)):
        if entry.startswith('.'):  # Ignore files or folders starting with a period
            continue
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            tree.append({
                'text': entry,
                'icon': 'jstree-folder',  # Folder icon
                'children': get_file_tree(full_path),
                'full_path': full_path
            })
        else:
            tree.append({
                'text': entry,
                'icon': 'jstree-file',  # File icon
                'full_path': full_path
            })
    return tree

def get_series_number_from_folder(folder_name):
    """
    Extracts the series number from a folder name if it matches the naming convention.
    Expecting the series number to be a zero-padded integer with 3-5 digits
    :param folder_name: The name of the folder.
    :return: The series number as an integer, or None if the folder name does not match. 
    """
    match = re.match(r'MR-SE(\d{3,5})-', folder_name)  # Match 3 to 5 digits
    if match:
        return int(match.group(1))
    return None

def get_server_environment():
    import getpass
    import os

    try:
        with open('/proc/self/comm', 'r') as f:
            process_name_proc = f.read().strip()
    except Exception:
        process_name_proc = None    

    env = {
        'username': getpass.getuser(),
        'cwd': os.getcwd(),
        'command_line': ' '.join(os.sys.argv), 
        'pid': os.getpid(),
        'data_folder': get_data_folder(),
        'process_root_folder': get_process_root_folder(),
        'module_folder': get_module_folder()
    }
    return env


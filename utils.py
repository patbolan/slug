import os
import re
import pydicom

DATA_DIR = '/home/bakken-raid8/pcad2/data'

def get_all_subjects():
    pattern = re.compile(r'^[A-Z]{3}-\d{4}$')  # Pattern for XXX-0000
    subjects = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d)) and pattern.match(d)]
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
    subject_path = os.path.join(DATA_DIR, subject_name)
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

def get_process_root_folder():
    #return '/home/bakken-raid8/pcad2/processes'
    return '/home/bakken-raid2/bolan/prj/slug/processes'

def get_process_file_path(process_id, file_relative_path=None):
    from process_manager import ProcessManager

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

def get_module_folder():
    return '/home/bakken-raid8/pcad2/modules/'

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


# Direct conversion from matlab
def guess_tag_from_seriesname(series_name, manufacturer):
    # Helper for case-insensitive substring search
    def ci_contains(haystack, needle):
        return needle.lower() in haystack.lower()
    
    # Set manufacturer variable
    manufact = ''
    if ci_contains(manufacturer, 'SIEMENS'):
        manufact = 'Siemens'
    elif ci_contains(manufacturer, 'Philips'):
        manufact = 'Philips'
    elif ci_contains(manufacturer, 'GE'):
        manufact = 'GE'
    
    series = ''
    
    # Siemens matching
    if ci_contains(manufacturer, 'SIEMENS'):
        manufact = 'Siemens'
        if ci_contains(series_name, 'b1map-6iso'):
            series = 'b1map'
        elif ci_contains(series_name, 'b1map'):
            series = 'b1map_x2'
        elif ci_contains(series_name, 't2_ana_axial'):
            series = 't2_ref'
        elif ci_contains(series_name, 'axial_1x1x1'):
            series = 'template'
        elif ci_contains(series_name, 'gre-axial'):
            series = 'thermo'
        elif ci_contains(series_name, 'vfa'):
            series = 't1_vfa'
        elif ci_contains(series_name, 'post_pelvis'):
            series = 't1_post'
        elif ci_contains(series_name, 'dynamic_sub'):
            series = 'dce_sub'
        elif ci_contains(series_name, 'dynamic'):
            series = 'dce_source'
        elif ci_contains(series_name, 'vibe'):
            series = 't1_vfa2'
        elif ci_contains(series_name, 'tse-ir'):
            series = 't1_tse'
        elif ci_contains(series_name, 'tfl_ti'):
            series = 't1_tfl'
        elif (ci_contains(series_name, 'semc') or ci_contains(series_name, 'se_mc')) and ci_contains(series_name, 'original'):
            series = 't2_semc2'
        elif (ci_contains(series_name, 'semc') or ci_contains(series_name, 'se_mc')) and ci_contains(series_name, '1x1x5'):
            series = 't2_semc'
        elif ci_contains(series_name, 't2map') or ci_contains(series_name, 't2_map'):
            series = 't2_semc'
        elif ci_contains(series_name, 'te101'):
            series = 't2_ref'
        elif ci_contains(series_name, 't2_tse_ax'):
            series = 't2_tse'
        elif ci_contains(series_name, 'b1600'):
            series = 'dwi_highb'
        elif ci_contains(series_name, 'space'):
            series = 't2_3d'
        elif ci_contains(series_name, '_trace') and ci_contains(series_name, 'zoomit'):
            series = 'dwi_source2'
        elif ci_contains(series_name, 'adc') and ci_contains(series_name, 'zoomit'):
            series = 'dwi_adc2'
        elif ci_contains(series_name, '_calc') and ci_contains(series_name, 'zoomit'):
            series = 'dwi_calc2'
        elif ci_contains(series_name, '_trace') and ci_contains(series_name, '-notzoomit'):
            series = 'dwi_source'
        elif ci_contains(series_name, 'adc') and ci_contains(series_name, '-notzoomit'):
            series = 'dwi_adc'
        elif ci_contains(series_name, '_calc') and ci_contains(series_name, '-notzoomit'):
            series = 'dwi_calc'
        else:
            series = ''
            manufact = ''
    
    # GE matching
    if ci_contains(manufacturer, 'GE'):
        manufact = 'GE'
        if ci_contains(series_name, 'b1map-optimized_rfdrive'):
            series = 'b1map'
        elif ci_contains(series_name, 'b1map-preset'):
            series = 'b1map_x2'
        elif ci_contains(series_name, 'b1map-quadrature'):
            series = 'b1map_x3'
        elif ci_contains(series_name, 'GRE-Axial_1x1x1') or ci_contains(series_name, 'Ax-1mm'):
            series = 'template'
        elif ci_contains(series_name, 'te_108') and not ci_contains(series_name, 'R_squared'):
            series = 't2_ref'
        elif ci_contains(series_name, 'tempmap'):
            series = 'thermo'
        elif ci_contains(series_name, 't1_vfa'):
            series = 't1_vfa'
        elif ci_contains(series_name, 'dce_flip'):
            series = 't1_vfa2'
        elif ci_contains(series_name, 'disco'):
            series = 't1_vfa2'
        elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR40')):
            series = 't1_smart1_hr40'
        elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR40')):
            series = 't1_smart1_hr40_raw'
        elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'T1_map[') and not ci_contains(series_name, 'orig') and ci_contains(series_name, 'HR70')):
            series = 't1_smart1_hr70'
        elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR70')):
            series = 't1_smart1_hr70_raw'
        elif ci_contains(series_name, 'fse_ir') and not ci_contains(series_name, 'R_squared'):
            series = 't1_tse'
        elif ci_contains(series_name, 'T2map') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig'):
            series = 't2_semc2'
        elif ci_contains(series_name, 'T2map') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig'):
            series = 't2_semc2_raw'
        elif ci_contains(series_name, 'pros_ax_t2') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig'):
            series = 't2_tse'
        elif ci_contains(series_name, 'pros_ax_t2') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig'):
            series = 't2_tse_raw'
        elif ci_contains(series_name, 'b1600'):
            series = 'dwi_highb'
        elif ci_contains(series_name, '3d_t2'):
            series = 't2_3d'
        elif ci_contains(series_name, 'dynamic'):
            series = 'dce_source'
        elif ci_contains(series_name, 'dynamic_sub'):
            series = 'dce_sub'
        elif ci_contains(series_name, 'post_pelvis'):
            series = 't1_post'
        elif ci_contains(series_name, 'dwi_b600') and not ci_contains(series_name, 'R_squared'):
            series = 'dwi_source'
        elif ci_contains(series_name, 'focus_b50_800') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'synthetic'):
            series = 'dwi_source2'
        elif ci_contains(series_name, 'dwi_b1000') and not ci_contains(series_name, 'synthetic'):
            series = 'dwi_source2_x2'
        else:
            series = ''
            manufact = ''
    
    # Philips matching
    if ci_contains(manufacturer, 'PHILIPS'):
        manufact = 'philips'
        if ci_contains(series_name, 'b1map'):
            series = 'b1map'
        elif ci_contains(series_name, 'te108'):
            series = 't2_ref'
        elif ci_contains(series_name, 't2w_tra_clin'):
            series = 't2_tse'
        elif ci_contains(series_name, 'thrive-match'):
            series = 'thermo'
        elif ci_contains(series_name, 'thrive-hires'):
            series = 'template'
        elif ci_contains(series_name, 'TVFA'):
            series = 't1_vfa_x2'
        elif ci_contains(series_name, 'mDIXON'):
            series = 't1_vfa2'
        elif ci_contains(series_name, 'IR_TSE'):
            series = 't1_tse'
        elif ci_contains(series_name, 'IRTFE'):
            series = 't1_tfl'
        elif ci_contains(series_name, '11echoes'):
            series = 't2_semc2'
        elif ci_contains(series_name, '32echoes'):
            series = 't2_semc'
        elif ci_contains(series_name, 'b1600'):
            series = 'dwi_highb'
        elif ci_contains(series_name, '3D_T2'):
            series = 't2_3d'
        elif ci_contains(series_name, 'post_pelvis'):
            series = 't1_post'
        elif ci_contains(series_name, '-Reg_-_DWI'):
            series = 'dwi_source2'
        elif ci_contains(series_name, '-dRegDWI'):
            series = 'dwi_adc2'
        elif ci_contains(series_name, '-eRegDWI'):
            series = 'dwi_calc2'
        else:
            series = ''
            manufact = ''
    
    tag = series
    return tag

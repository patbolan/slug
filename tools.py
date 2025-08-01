from utils import get_study_file_path, get_study_path, get_module_folder, get_series_number_from_folder, get_sample_dicom_header
import os
import subprocess
import shutil
import time
import glob
from datetime import datetime
from multiprocessing import Process, Pipe
from process_manager import ProcessManager
from abc import ABC
import sys
import io
import pydicom
import tempfile


# Refactor plan: Utility functions in tool_utilities.py. Base and subclasses in their own files


###############################################################################
# Tool Utilities
###############################################################################
def get_tools_for_study(subject_name, study_name):

    # returns a list of tools, each as a dictionary summarizing its current state
    simple_tool = SimpleTool(subject_name, study_name)
    nii_converter = NiiConverter(subject_name, study_name)  
    dicom_raw_storage_cleaner = DicomRawStorageCleaner(subject_name, study_name)
    autotagger = AutoTagger(subject_name, study_name)
    template_registration = TemplateRegistration(subject_name, study_name)
    reslice_mask = ResliceMask(subject_name, study_name)

    # Consider only adding the raw storage cleaner if it's a Philips study

    # Put all tools (actually their status dictionaries) in a list
    toolset = [dicom_raw_storage_cleaner.get_status_dict(), 
               autotagger.get_status_dict(),
               nii_converter.get_status_dict(), 
               template_registration.get_status_dict(), 
               reslice_mask.get_status_dict(),]

    return toolset

def execute_tool(tool_name, command, subject_name, study_name):
    """
    Execute a tool command
    :param tool_name: Name of the tool.
    :param command: Command to execute (e.g., 'run', 'undo').
    :param subject_name: Subject name.
    :param study_name: Study name.
    """
    if tool_name == 'nii-converter':
        tool = NiiConverter(subject_name, study_name)
    elif tool_name == 'simple-tool': # Simple tool for testing
        tool = SimpleTool(subject_name, study_name)
    elif tool_name == 'dicom-raw-storage-cleaner':
        tool = DicomRawStorageCleaner(subject_name, study_name)
    elif tool_name == 'autotagger':
        tool = AutoTagger(subject_name, study_name)
    elif tool_name == 'template-registration':
        tool = TemplateRegistration(subject_name, study_name)
    elif tool_name == 'reslice-mask':
        tool = ResliceMask(subject_name, study_name)
    else:
        raise ValueError(f"Unknown tool '{tool_name}'") 
            
    # Now run the command on the tool object
    if command == 'run':
        tool.run_in_subprocess()

    elif command == 'undo':
        tool.undo()

    else:
        raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")


'''
Tools have four possible states:
- unavailable: inputs do not exist
- available: ready to run, no outputs exist
- running: currently executing, outputs may exist but are not complete
- complete: has run successfully, outputs exist
'''
class Tool(ABC):
    """
    Abstract base class for tools.
    Each tool should implement the get_status_dict, run, and undo methods.
    """
    # Initialize with the context of the tool, which includes subject name, study name, and file path 
    # These parameters help to determine the scope of the tool
    # e.g., whether it operates at the project level, subject level, or study level
    def __init__(self, subject_name=None, study_name=None, file_path=None):
        self.subject_name = subject_name # if no subject, project-level tool
        self.study_name = study_name # if no study, subject-level tool
        self.file_path = file_path  # if no file_path, study-level tool
        self.name = 'base-tool' # Placeholder name, should be overridden by subclasses 
    
    def get_context(self):
        return {
            'subject_name': self.subject_name,
            'study_name': self.study_name,
            'file_path': self.file_path
        }

    def run(self):
        raise NotImplementedError("Subclasses should implement this method")
    
    # This creates a subprocess to run the tool's run method asynchronously and capture the output
    def run_in_subprocess(self):
        pm = ProcessManager()
        ipid = pm.spawn_process(tool=self, command='run', mode='sync') # mode is sync or async
        print(f"Started asynchronous process for {self.name} with command 'run', ipid={ipid}") 

    def undo(self):
        raise NotImplementedError("Subclasses should implement this method")
    
    # Some tools are not undable
    def is_undoable(self):
        return True

    # Check if the output files exist for this tool. Should be overridden by subclasses.
    # This is used to determine the status of the tool.
    def output_files_exist(self):
        raise NotImplementedError("Subclasses should implement this method")
    
    # Check if the input files exist for this tool. Should be overridden by subclasses.
    # This is used to determine the if the tool can be run.
    # If not overridden, it defaults to True, meaning the tool can be run without checking
    def input_files_exist(self):
        return True
    
    # Get the status of the tool as a dictionary.
    # This includes the name, status, message, commands available, and process ID if applicable
    # Status can be 'available', 'running', or 'complete'
    # Commands can be 'run', 'undo', or empty if not applicable
    # Returns a dictionary with the tool's status which can be used in the UI
    def get_status_dict(self):
        # See if there is a running process first. This is inefficient
        pm = ProcessManager()
        pid = pm.get_process_id(self.subject_name, self.study_name, self.name)
        if pm.is_running(pid): 
                print(f'Found running process {pid}')
                tool_status = 'running'
                message = f'{self.name} is running, refresh page to update'
                commands = []        
        else: 
            print(f'Process {pid} is not running')
            # Either can't find process, or it is completed. Check outputs
            if self.output_files_exist():
                tool_status = 'complete'
                message = f'{self.name} has run successfully'
                if self.is_undoable():
                    commands = ['undo']
                else:
                    commands = []
            elif self.input_files_exist():
                pid = None # It may have ran before
                tool_status = 'available'
                message = f'{self.name} is ready to run'
                commands = ['run']
            else:
                pid = None
                tool_status = 'unavailable'
                message = f'{self.name} cannot run, inputs do not exist'    
                commands = []

        return {
            'name': self.name,
            'status': tool_status,
            'message': message,
            'commands': commands,
            'pid': pid
        }
    
    # Helper function to print the output and error messages from a subprocess
    # This is used to print the output of the command run in the run method
    def print_subprocess_output(self, result):
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            raise Exception(f"Command failed: {result.stderr}")
        else:
            print(f"Command completed successfully with return code {result.returncode}")
        if result.stdout:
            print('Standard Output:')
            print(result.stdout)
        if result.stderr:
            print('Standard Error:')
            print(result.stderr)    
        else: 
            print('No errors.') 




# A simple tool for testing purposes.
# It simulates a long-running process by sleeping for 5 seconds and creates a test file
class SimpleTool(Tool):

    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'simple-tool'

        # Specify the test file path
        self.test_file_path = os.path.join(get_study_file_path(self.subject_name, self.study_name, 'testfile.txt'))

    def output_files_exist(self):
        return os.path.isfile(self.test_file_path)

    def run(self):
        print(f"Running simple tool {self.name} for subject {self.subject_name} and study {self.study_name}")

        print('Sleeping for 5s as a test....')
        time.sleep(5)
        print('.... done sleeping.')

        # Create a dummy file in the study folder
        with open(self.test_file_path, 'w') as f:
            f.write(f"This is a test file for {self.name} in study {self.study_name} for subject {self.subject_name}\n")    

    def undo(self):
        print(f"Undoing simple tool {self.name} for subject {self.subject_name} and study {self.study_name}")
        if os.path.isfile(self.test_file_path):
            os.remove(self.test_file_path)


# A tool for finding special Dicom Raw Storage files and removing them from the dicom-original folder tree
# In some Philips datasets there is a Raw Storage file, SOP Class UID = 1.2.840.10008.5.1.4.1.1.66. 
# The presence of htis file probably depends on how the data were exported.
# This function will look through all the dicom-original folders looking
# for these raw data files, determined by their SOPClassUID. If any are
# found they are moved to a folder called dicom-raw-storatge, because these will break all the
# other tools.
#
# This tool will create the dicom-raw-storage folder if it does not exist regardless of whether it finds any files, 
# just so you can tell that the tool has run.
class DicomRawStorageCleaner(Tool):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'dicom-raw-storage-cleaner'
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        
        # don't create the raw storage folder here, it will be created in the run method if needed
        self.dicom_raw_storage_path = get_study_file_path(subject_name, study_name, 'dicom-raw-storage')

    def output_files_exist(self):
        # Check for the dicom-raw-storage folder
        return os.path.isdir(self.dicom_raw_storage_path)

    def input_files_exist(self):
        # Check if the dicom-original folder exists. Don't look for contents, just the folder
        return os.path.isdir(self.dicom_original_path)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Create the raw storage folder if it does not exist
        if not os.path.exists(self.dicom_raw_storage_path):
            os.makedirs(self.dicom_raw_storage_path)

        # Look at all files in the dicom-original folder recursively
        dicom_files = [f for f in glob.glob(os.path.join(self.dicom_original_path, '**'), recursive=True) if os.path.isfile(f)]

        print(f"Found {len(dicom_files)} DICOM files in {self.dicom_original_path}. Searching for raw storage files...")        
        raw_storage_files = []
        for dicom_file in dicom_files:  
            print(f'Checking DICOM file: {dicom_file}')
            try:
                dicom_data = pydicom.dcmread(dicom_file, stop_before_pixels=True)
                print(f'  DICOM file {dicom_file} SOPClassUID: {dicom_data.SOPClassUID}')
                if dicom_data.SOPClassUID == '1.2.840.10008.5.1.4.1.1.66':
                    raw_storage_files.append(dicom_file)
                    print(f"Found raw storage file: {dicom_file}")
            except Exception as e:
                print(f"Error reading DICOM file {dicom_file}: {e}")    
        
        if not raw_storage_files:   
            print(f"No raw storage files found in {self.dicom_original_path}. Nothing to do.")
        else:   
            print(f"Found {len(raw_storage_files)} raw storage files. Moving them to {self.dicom_raw_storage_path}...")

            # Move the raw storage files to the raw storage folder
            for raw_file in raw_storage_files:
                shutil.move(raw_file, self.dicom_raw_storage_path)
                print(f"Moved {raw_file} to {self.dicom_raw_storage_path}")

    def is_undoable(self):
        return False

    def undo(self):
        raise NotImplementedError(f"{self.name} does not support undo. Need to do this manually.")
    

# The NiiConverter class is a tool for converting DICOM files to NIfTI format.
class NiiConverter(Tool):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'nii-converter'

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        self.dicom_tags_file = os.path.join(get_study_file_path(subject_name, study_name, 'dicom_tags.csv'))

    def output_files_exist(self):
        return os.path.isdir(self.nii_folder)
    
    def input_files_exist(self):
        # Needs both the dicom_tags.csv file and the dicom-original folder to exist
        return os.path.isdir(self.dicom_original_path) and os.path.isfile(self.dicom_tags_file)
    
    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = get_module_folder()
        module_script = os.path.join(module_folder, 'convert2nii', 'run.sh')
        study_folder = get_study_path(self.subject_name, self.study_name)
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!
        print(f"***** Running command: {cmd}")

        # Run the command in a subprocess
        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )
        # If you need the pid you can replace subprocess.run() with subprocess.Popen(), but 
        # it takes a little more code

        # Print the output and error messages
        self.print_subprocess_output(result)

    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"{self.name} cannot undo: {status_dict['message']}")

        print(f"Deleting nii folder {self.nii_folder}")
        if os.path.exists(self.nii_folder):
            shutil.rmtree(self.nii_folder)

        

class TemplateRegistration(Tool):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'template-registration'

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.thermo_file = os.path.join(self.nii_folder, 'thermo.nii')
        self.template_file = os.path.join(self.nii_folder, 'template.nii')

    def output_files_exist(self):
        return os.path.isfile(self.template_file)
    
    def input_files_exist(self):
        return os.path.isfile(self.thermo_file)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = get_module_folder()
        module_script = os.path.join(module_folder, 'registration', 'run_registration.sh')
        study_folder = get_study_path(self.subject_name, self.study_name)
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!
        print(f"***** Running command: {cmd}")

        # Run the command in a subprocess
        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )

        # Print the output and error messages
        self.print_subprocess_output(result)

    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"{self.name} cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting template.nii ")
        if os.path.exists(self.template_file):
            os.remove(self.template_file)



class ResliceMask(Tool):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'reslice-mask'

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.template_file = os.path.join(self.nii_folder, 'template.nii')

    def output_files_exist(self):
        if not os.path.isdir(self.nii_folder):  
            return False

        if os.path.isdir(self.nii_folder):
            # look for files ending in '_mask.nii'
            mask_files = [f for f in os.listdir(self.nii_folder) if f.endswith('_mask.nii')]
            return (len(mask_files) > 0)
    
    def input_files_exist(self):
        return os.path.isfile(self.template_file)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = get_module_folder()
        module_script = os.path.join(module_folder, 'registration', 'run_reslice_mask.sh')
        study_folder = get_study_path(self.subject_name, self.study_name)
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!
        print(f"***** Running command: {cmd}")

        # Run the command in a subprocess
        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )

        # Print the output and error messages
        self.print_subprocess_output(result)

    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"{self.name} cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting all _mask.nii files in {self.nii_folder}")
        mask_files = [f for f in os.listdir(self.nii_folder) if f.endswith('_mask.nii')]    
        for mask_file in mask_files:
            full_mask_path = os.path.join(self.nii_folder, mask_file)
            print(f"Deleting {full_mask_path}")
            if os.path.exists(full_mask_path):
                os.remove(full_mask_path)




# Implements logic for identifying dicom series, applying tags, and storing them in the dicom_tags.csv file
class AutoTagger(Tool):

    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'autotagger'

        # Specify the test file path and dicom folder
        self.tag_file = os.path.join(get_study_file_path(self.subject_name, self.study_name, 'dicom_tags.csv'))
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        self.study_folder = get_study_path(subject_name, study_name)

    def input_files_exist(self):
        return os.path.isdir(self.dicom_original_path)
    
    def output_files_exist(self):
        return os.path.isfile(self.tag_file)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Get a list of dicom series folders
        series_folders = [f for f in glob.glob(os.path.join(self.dicom_original_path, '**'), recursive=True) if os.path.isdir(f)]
        series_folders.sort()

        # Create the dicom_tags.csv file (it should not exist already)
        assert not os.path.isfile(self.tag_file), f"Tag file {self.tag_file} already exists. Should not happen."

        # I write to a temporary file first, then move it to the final location to prevent other processses 
        # reading a half-written file. Note I write the temp file in the study folder so it can be copied. If 
        # you write it in /tmp, then os.replace() can fail since its on a different filesystem.
        with tempfile.NamedTemporaryFile('w', dir=self.study_folder, delete=False) as tf:
            tempname = tf.name
            tf.write(f'seriesnum,tag\n')
            for series_folder in series_folders:
                series_name = os.path.basename(series_folder)
                series_number = get_series_number_from_folder(series_name)
                if series_number is None:
                    print(f"Skipping folder {series_name} as it does not have a valid series number")
                    continue

                hdr = get_sample_dicom_header(self.subject_name, self.study_name, series_name)
                manufacturer = hdr.get('Manufacturer', 'Unknown') if hdr else 'Unknown'

                print(f"Processing series {series_number} with name '{series_name}' and manufacturer '{manufacturer}'")
                
                # Guess the tag from the series name and manufacturer
                tag = self.guess_tag_from_seriesname(series_name, manufacturer)
                if tag:
                    tf.write(f'{series_number},{tag}\n')
                    print(f"Tagged series {series_number} with tag '{tag}'")
                else:
                    tf.write(f'{series_number},\n')
                    print(f"No tag found for series {series_number} with name '{series_name}' and manufacturer '{manufacturer}'")
        
        # Now move the temporary file to the final tag file location
        os.replace(tempname, self.tag_file)

    # Disable this undo - I don't want to delete the tags file so easily
    def is_undoable(self):
        return True
    
    def undo(self):
        print(f"Undoing {self.name} for subject {self.subject_name} and study {self.study_name}")
        if os.path.isfile(self.tag_file):
            os.remove(self.tag_file)


    # Direct conversion from matlab
    def guess_tag_from_seriesname(self, series_name, manufacturer):
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

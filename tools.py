from utils import get_study_file_path, get_study_path, get_module_folder
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


'''
Tools have four possible states:
- unavailable: inputs do not exist
- available: ready to run, no outputs exist
- running: currently executing, outputs may exist but are not complete
- complete: has run successfully, outputs exist
'''
def get_tools_for_study(subject_name, study_name):

    # returns a list of tools, each as a dictionary summarizing its current state
    simple_tool = SimpleTool(subject_name, study_name)
    nii_converter = NiiConverter(subject_name, study_name)  
    dicom_raw_storage_cleaner = DicomRawStorageCleaner(subject_name, study_name)

    # Consider only adding the raw storage cleaner if it's a Philips study

    # Put all tools (actually their status dictionaries) in a list
    #toolset = [simple_tool.get_status_dict(), nii_converter.get_status_dict()]
    toolset = [simple_tool.get_status_dict(), 
               dicom_raw_storage_cleaner.get_status_dict(), 
               nii_converter.get_status_dict()]


    return toolset

def execute_tool(tool_name, command, subject_name, study_name, async_mode=True):
    """
    Execute a tool command, either synchronously or asynchronously.
    :param tool_name: Name of the tool.
    :param command: Command to execute (e.g., 'run', 'undo').
    :param subject_name: Subject name.
    :param study_name: Study name.
    :param async_mode: If True, execute the command asynchronously.
    """
    if tool_name == 'nii-converter':
        tool = NiiConverter(subject_name, study_name)
    elif tool_name == 'simple-tool': # Simple tool for testing
        tool = SimpleTool(subject_name, study_name)
    elif tool_name == 'dicom-raw-storage-cleaner':
        tool = DicomRawStorageCleaner(subject_name, study_name)
    else:
        raise ValueError(f"Unknown tool '{tool_name}'")
            
    # Now run the command on the tool object
    if command == 'run':
        if async_mode:
            pm = ProcessManager()
            ipid = pm.spawn_process(tool=tool, command='run')
            print(f"Started asynchronous process for {tool_name} with command '{command}', ipid={ipid}") 
        else:
            tool.run()

    elif command == 'undo':
        tool.undo()

    else:
        raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")
                
    

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
                pid = None # It may have ran before, but don't like to that pid - confusing
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

    def output_files_exist(self):
        return os.path.isdir(self.nii_folder)
    
    def input_files_exist(self):
        # Check if the dicom-original folder exists. Don't look for contents, just the folder
        return os.path.isdir(self.dicom_original_path)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = get_module_folder()
        module_script = os.path.join(module_folder, 'convert2nii', 'run.sh')
        study_folder = get_study_path(self.subject_name, self.study_name)
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!
        print(f"***** Running command: {cmd}")

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
            raise Exception(f"NiiConverter cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting nii folder {self.nii_folder}")
        if os.path.exists(self.nii_folder):
            shutil.rmtree(self.nii_folder)





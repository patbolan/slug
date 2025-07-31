from utils import get_study_file_path, get_study_path
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


def get_tools_for_study(subject_name, study_name):

    # returns a list of tools, each as a dictionary summarizing its current state
    simple_tool = SimpleTool(subject_name, study_name)
    nii_converter = NiiConverter(subject_name, study_name)  

    # Put all tools (actually their status dictionaries) in a list
    toolset = [simple_tool.get_status_dict(), nii_converter.get_status_dict()]
    #toolset = [simple_tool.get_status_dict()]

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
        nii_converter = NiiConverter(subject_name, study_name)
        if command == 'run':

            if async_mode:
                pm = ProcessManager()
                ipid = pm.spawn_process(tool=nii_converter, command='run')
                #print(f"Started asynchronous process for {tool_name} with command '{command}', ipid={ipid}") 

            else:
                nii_converter.run()

        elif command == 'undo':
            nii_converter.undo()
        else:
            raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")
                
    elif tool_name == 'simple-tool': # Simple tool for testing
        simple_tool = SimpleTool(subject_name, study_name)
        if command == 'run':

            if async_mode:
                pm = ProcessManager()
                ipid = pm.spawn_process(tool=simple_tool, command='run')
                #print(f"Started asynchronous process for {tool_name} with command '{command}', ipid={ipid}") 

            else:
                simple_tool.run()

        elif command == 'undo':
            simple_tool.undo()
        else:
            raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")

    else:
        raise ValueError(f"Unknown tool '{tool_name}'")
    

class Tool(ABC):
    """
    Abstract base class for tools.
    Each tool should implement the get_status_dict, run, and undo methods.
    """
    def get_status_dict(self):
        raise NotImplementedError("Subclasses should implement this method")
    
    # Tools can operate at the subject, study, or project level. 
    def get_context(self):
        return {
            'subject_name': '',
            'study_name': '',
            'file_path': ''
        }

    def run(self):
        raise NotImplementedError("Subclasses should implement this method")

    def undo(self):
        raise NotImplementedError("Subclasses should implement this method")

    def get_context(self):
        return {
            'subject_name': self.subject_name,
            'study_name': self.study_name,
            'file_path': '' # Operating on a study, not a path
        }


class SimpleTool(Tool):
    """
    A simple tool for testing purposes.
    """
    def __init__(self, subject_name, study_name):
        self.name = 'simple-tool'
        self.subject_name = subject_name
        self.study_name = study_name

        # Specify the test file path
        self.test_file_path = os.path.join(get_study_file_path(self.subject_name, self.study_name, 'testfile.txt'))


    def get_status_dict(self):
        # See if there is a running process first. This is inefficient
        pm = ProcessManager()
        pid = pm.get_process_id(self.subject_name, self.study_name, self.name)
        if pm.is_running(pid): 
                print(f'Found running process {pid}')
                tool_status = 'running'
                message = 'Simple tool is running, refresh page to update'
                commands = []        
        else: 
            print(f'Process {pid} is not running')
            # Either can't find process, or it is completed. Check outputs
            if os.path.isfile(self.test_file_path):
                tool_status = 'complete'
                message = 'Simple tool has run successfully'
                commands = ['undo']
            else:
                pid = None # It may have ran before, but don't like to that pid - confusing
                tool_status = 'available'
                message = 'Simple tool is ready to run'
                commands = ['run']

        return {
            'name': self.name,
            'status': tool_status,
            'message': message,
            'commands': commands,
            'pid': pid
        }

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






###############################################################################
# The NiiConverter class is a tool for converting DICOM files to NIfTI format.
# Currently not used - will come back to it

class NiiConverter(Tool):
    def __init__(self, subject_name, study_name):
        self.name = 'nii-converter'
        self.subject_name = subject_name
        self.study_name = study_name

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')

    # returns status, message
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
            if os.path.isdir(self.nii_folder):
                tool_status = 'complete'
                message = f'{self.name} has run successfully'
                commands = ['undo']
            else:
                pid = None # It may have ran before, but don't like to that pid - confusing
                tool_status = 'available'
                message = f'{self.name} is ready to run'
                commands = ['run']

        return {
            'name': self.name,
            'status': tool_status,
            'message': message,
            'commands': commands,
            'pid': pid
        }
        

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = '/home/bakken-raid8/pcad2/modules/'
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




    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"NiiConverter cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting nii folder {self.nii_folder}")
        if os.path.exists(self.nii_folder):
            shutil.rmtree(self.nii_folder)





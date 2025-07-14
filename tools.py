from utils import get_study_file_path, get_study_path
import os
import subprocess
import shutil
import time
import glob
from datetime import datetime
from multiprocessing import Process

def get_tools_for_study(subject_name, study_name):

    # returns a list of tools, each as a dictionary summarizing its current state
    nii_converter = NiiConverter(subject_name, study_name)  
    toolset = [nii_converter.get_status_dict()]

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
        process_name = f'slug-{tool_name}'
        if command == 'run':
            if async_mode:
                # Run asynchronously in a separate process
                process = Process(name=process_name, target=nii_converter.run)
                process.start()
                print(f"Started asynchronous process for {tool_name} with command '{command}'")
                this_process = os.getpid()
                print(f"pid={process.pid}, parent={this_process}, {process.name}")

            else:
                # Run synchronously
                nii_converter.run()
        elif command == 'undo':
            nii_converter.undo()
        else:
            raise ValueError(f"Unknown command '{command}' for tool '{tool_name}'")
    else:
        raise ValueError(f"Unknown tool '{tool_name}'")


class NiiConverter:
    def __init__(self, subject_name, study_name):
        self.subject_name = subject_name
        self.study_name = study_name
        self.tool_name = 'nii-converter'

        # Temporoary folder
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')

    # returns status, message
    def get_status_dict(self):

        # Look for a running process
        study_process_folder_running = get_study_file_path(self.subject_name, self.study_name, os.path.join('processes', 'running'))  
        running_processes = glob.glob(os.path.join(study_process_folder_running, f'*{self.tool_name}*'))
        if running_processes:
            status = 'running'
            message = 'refresh page to update'
            commands = []
        else:
            # Check for nii-original
            if os.path.exists(self.nii_folder):
                status = 'complete'
                message = 'nii-original folder exists'
                commands = ['undo']
            else:
                # Check for pre-reqs
                if os.path.exists(self.dicom_original_path):
                    status = 'available'
                    message = 'dicom-original found, ready to convert'
                    commands = ['run']
                else:
                    status = 'unavailable'
                    message = 'dicom-original not found'
                    commands = []

        # Format and return descriptor dictionary   
        return {'name': self.tool_name,
                'status': status,
                'message': message,
                'commands': commands}
        

    # Dummy functions, create and delete a folder "nii-temp"
    def run(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'available':
            raise Exception(f"NiiConverter cannot run: {status_dict['message']}")

        # Run the module, a command-line script
        module_folder = '/home/bakken-raid8/pcad2/modules/'
        module_script = os.path.join(module_folder, 'convert2nii', 'run.sh')
        study_folder = get_study_path(self.subject_name, self.study_name)
        #cmd = f'{module_script} {study_folder}'
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!
        print(f"Running command: {cmd}")

        # Prep a process folder
        study_process_folder_running = get_study_file_path(self.subject_name, self.study_name, os.path.join('processes', 'running'))    
        study_process_folder_completed = get_study_file_path(self.subject_name, self.study_name, os.path.join('processes', 'completed'))    
        if not os.path.exists(study_process_folder_running):
            os.makedirs(study_process_folder_running)
        if not os.path.exists(study_process_folder_completed):
            os.makedirs(study_process_folder_completed)

        # This process
        this_process_folder_name = f'{datetime.now().isoformat()}-{self.tool_name}-run'
        this_process_folder = os.path.join(study_process_folder_running, this_process_folder_name)
        print(f'Creating {this_process_folder}')
        if not os.path.exists(this_process_folder):
            os.makedirs(this_process_folder)

        with open(os.path.join(this_process_folder, 'command.txt'), 'w') as f:
            f.write(' '.join(cmd))

        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )
        print('Result:')
        print(result)

        # Add 10s pause 
        time.sleep(10)
                
        # result.returncode is 0 if sucessful
        print(f'Completed with return code: {result.returncode}')

        with open(os.path.join(this_process_folder, 'stdout.txt'), 'w') as f:
            f.write(result.stdout + '\n')
        with open(os.path.join(this_process_folder, 'stderr.txt'), 'w') as f:
            f.write(result.stderr + '\n')
        with open(os.path.join(this_process_folder, 'returncode.txt'), 'w') as f:
            f.write(f'{result.returncode}\n')

        # Now move this process to completed
        shutil.move(this_process_folder, study_process_folder_completed)

        return result


    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"NiiConverter cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting nii folder {self.nii_folder}")
        if os.path.exists(self.nii_folder):
            shutil.rmtree(self.nii_folder)





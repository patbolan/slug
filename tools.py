from utils import *
import os
import subprocess
import shutil


def get_tools_for_study(subject_name, study_name):

    # returns a list of tools
    # HARDWIRED
    # toolset = [ 
    #     {'name': 'NiiConverter', 'status': 'complete', 'commands':['undo'] }, 
    #     {'name': 'T2Mapping', 'status': 'available', 'commands':['run'] }, 
    #     {'name': 'Segmentation', 'status': 'unavailable', 'message':'Not yet implemented', 'commands':[] }, 
    # ]

    nii_converter = NiiConverter(subject_name, study_name)  
    toolset = [nii_converter.get_status_dict()]

    return toolset

def execute_tool(tool_name, command, subject_name, study_name):
    # Execute a tool command
    if tool_name == 'nii-converter':
        nii_converter = NiiConverter(subject_name, study_name)
        if command == 'run':
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

        # Temporoary folder
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')

    # returns status, message
    def get_status_dict(self):

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
        return {'name': 'nii-converter',
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


        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )

        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        print("Return Code:", result.returncode)

        return result


    def undo(self):
        status_dict = self.get_status_dict()
        if status_dict['status'] != 'complete':
            raise Exception(f"NiiConverter cannot undo: {status_dict['message']}")

        # Simulate undo (replace with actual undo logic)
        print(f"Deleting nii folder {self.nii_folder}")
        if os.path.exists(self.nii_folder):
            shutil.rmtree(self.nii_folder)





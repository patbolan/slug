"""
ResliceMask Tool
This tool reslices a mask to match a template image using a command-line script.

See NiiConverter.py header for more information about wrapping a "module"
"""

import os
import subprocess
from .tool_base import ToolBase
from utils import get_study_file_path, get_study_path, get_module_folder

class ResliceMask(ToolBase):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'reslice-mask'

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.template_file = os.path.join(self.nii_folder, 'template.nii')

    def are_output_files_present(self):
        if not os.path.isdir(self.nii_folder):  
            return False

        if os.path.isdir(self.nii_folder):
            # look for files ending in '_mask.nii'
            mask_files = [f for f in os.listdir(self.nii_folder) if f.endswith('_mask.nii')]
            return (len(mask_files) > 0)
    
    def are_input_files_present(self):
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
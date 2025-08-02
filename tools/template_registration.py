"""
TemplateRegistration Tool
This tool is responsible for registering a template to the phantom images
so the quantitative values can be extracted.

See NiiConverter.py header for more information about wrapping a "module"
"""

import os
import subprocess
from .tool_base import ToolBase
from utils import get_study_file_path, get_study_path, get_module_folder

class TemplateRegistration(ToolBase):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'template-registration'

        # Folder paths
        self.nii_folder = get_study_file_path(subject_name, study_name, 'nii-original')
        self.thermo_file = os.path.join(self.nii_folder, 'thermo.nii')
        self.template_file = os.path.join(self.nii_folder, 'template.nii')

    def are_output_files_present(self):
        return os.path.isfile(self.template_file)
    
    def are_input_files_present(self):
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
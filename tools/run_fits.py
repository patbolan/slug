"""
RunFits Tool
This tool is a wrapper for the run_all_fits.sh script

This is a big wrapper. 

See NiiConverter.py header for more information about wrapping a "module"
"""

import os
import subprocess
from .tool_base import ToolBase
from utils import get_study_file_path, get_study_path, get_module_folder

class RunFits(ToolBase):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'run-all-fits'

    # I can't really tell the conditions
    def are_output_files_present(self):
        return False
    
    def are_input_files_present(self):
        return True

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Run the module, a command-line script
        module_folder = get_module_folder()
        module_script = os.path.join(module_folder, 'fitting', 'run_all_fits.sh')

        study_folder = get_study_path(self.subject_name, self.study_name)
        cmd = [module_script, study_folder] # Important: cmd is a list, not a string with spaces!

        # HACK just do T2 this time
        # module_script = os.path.join(module_folder, 'fitting', 'run_t2_tse.sh')        
        # cmd = [module_script, '-i', study_folder, '-t', 't2_tse', '-s', 'both', '-f', 'both'] # Important: cmd is a list, not a string with spaces!

        print(f"***** Running module command: {cmd}")

        # Run the command in a subprocess
        result = subprocess.run(
            cmd,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )

        # Print the output and error messages
        self.print_subprocess_output(result)
    
    def is_undoable(self):
        return False

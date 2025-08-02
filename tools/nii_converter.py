import os
import subprocess
import shutil
from .tool import Tool
from utils import get_study_file_path, get_study_path, get_module_folder

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
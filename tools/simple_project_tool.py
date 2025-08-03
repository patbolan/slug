"""
SimpleProject Tool

A testing tool that operates on the project level. 
I creates a simple text file (subject_count.txt) with the number of subjects in the project.
It can also delete this file.
It is used to test the tool framework.
"""

import os
import time
from .tool_base import ToolBase
from utils import get_all_subjects, get_data_folder

class SimpleProjectTool(ToolBase):
    def __init__(self):
        super().__init__()
        self.name = 'simple-project-tool'
        self.output_file = os.path.join(get_data_folder(), 'Project_Reports', 'subject_count.txt')

    def are_output_files_present(self):
        return os.path.isfile(self.output_file)

    def run(self):
        print(f"Running {self.name} ")
        subjects = get_all_subjects()

        with open(self.output_file, 'w') as f:
            f.write(f"This project has {len(subjects)} subjects.\n")

    def undo(self):
        if os.path.isfile(self.output_file):
            os.remove(self.output_file)
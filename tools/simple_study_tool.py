"""
SimpleTool Tool

A testing tool that just creates and deletes a file. 
"""

import os
import time
from .tool_base import ToolBase
from utils import get_study_file_path

class SimpleStudyTool(ToolBase):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'simple-study-tool'
        self.test_file_path = os.path.join(get_study_file_path(self.subject_name, self.study_name, 'testfile.txt'))

    def are_output_files_present(self):
        return os.path.isfile(self.test_file_path)

    def run(self):
        print(f"Running simple tool {self.name} for subject {self.subject_name} and study {self.study_name}")
        time.sleep(5)
        with open(self.test_file_path, 'w') as f:
            f.write(f"This is a test file for {self.name} in study {self.study_name} for subject {self.subject_name}\n")

    def undo(self):
        if os.path.isfile(self.test_file_path):
            os.remove(self.test_file_path)
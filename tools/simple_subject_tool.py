"""
SimpleSubject Tool

A testing tool that operates ona a subject level. 
I creates a simple text file (study_count.txt) with the number of studies for the subject.
It can also delete this file.
It is used to test the tool framework.
"""

import os
import time
from .tool_base import ToolBase
from utils import get_subject_path, get_studies_for_subject

class SimpleSubjectTool(ToolBase):
    def __init__(self, subject_name):
        super().__init__(subject_name)
        self.name = 'simple-subject-tool'
        self.output_file = os.path.join(get_subject_path(subject_name), 'Subject_Reports', 'study_count.txt')

    def are_output_files_present(self):
        return os.path.isfile(self.output_file)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} ")
        studies = get_studies_for_subject(self.subject_name)

        with open(self.output_file, 'w') as f:
            f.write(f"This subject {self.subject_name} has {len(studies)} studies.\n")

    def undo(self):
        if os.path.isfile(self.output_file):
            os.remove(self.output_file)
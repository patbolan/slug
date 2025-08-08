"""
ToolBase Abstract Class

This module defines the `ToolBase` abstract class, which serves as the base
class for all tools in the application. It provides a common interface and
shared functionality for tools, such as managing context, running processes,
and determining tool status.

Key Features:
- Defines the interface for tools with abstract methods (`run`, `undo`).
- Provides shared methods for running tools in subprocesses.
- Implements logic for determining tool status (e.g., running, complete).
- Supports undo functionality for tools.

Classes:
- ToolBase: Abstract base class for tools.

Dependencies:
- Python Standard Libraries: abc
- Custom Modules: tools.process_manager (for managing subprocesses)

Author: Patrick Bolan
Date: Aug 2025
"""

from abc import ABC
from tools.process_manager import ProcessManager

class ToolBase(ABC):
    def __init__(self, subject_name=None, study_name=None, file_path=None):
        self.subject_name = subject_name
        self.study_name = study_name
        self.file_path = file_path
        self.name = 'base-tool'

    def get_context(self):
        return {
            'subject_name': self.subject_name,
            'study_name': self.study_name,
            'file_path': self.file_path,
        }

    # Note when override rideing this method use "print" not loggers
    def run(self):
        raise NotImplementedError("Subclasses should implement this method")

    def run_in_subprocess(self):
        pm = ProcessManager()
        ipid = pm.spawn_process(tool=self, command='run', mode='sync')
        print(f"Started asynchronous process for {self.name} with command 'run', ipid={ipid}")

    def undo(self):
        raise NotImplementedError("Subclasses should implement this method")

    def is_undoable(self):
        return True

    # These two methods are used to check if output/input files exist, which is used
    # to determine if the tool can run or has already run. Subclasses should probably
    # override
    def are_output_files_present(self):
        return False

    def are_input_files_present(self):
        return True

    def get_status_dict(self):
        """
        Returns a dictionary with the status of the tool.
        The status can be 'running', 'complete', 'available', or 'unavailable'.
        This dictionary is used by the UI to display the status of the tool and
        what commands can be run
        """
        pm = ProcessManager()
        pid = pm.get_process_id(self.subject_name, self.study_name, self.name)
        if pm.is_running(pid):
            return {
                'name': self.name,
                'status': 'running',
                'message': f'{self.name} is running, refresh page to update',
                'commands': [],
                'pid': pid,
            }
        elif self.are_output_files_present():
            return {
                'name': self.name,
                'status': 'complete',
                'message': f'{self.name} has run successfully',
                'commands': ['undo'] if self.is_undoable() else [],
                'pid': pid,
            }
        elif self.are_input_files_present():
            return {
                'name': self.name,
                'status': 'available',
                'message': f'{self.name} is ready to run',
                'commands': ['run'],
                'pid': None,
            }
        else:
            return {
                'name': self.name,
                'status': 'unavailable',
                'message': f'{self.name} cannot run, inputs do not exist',
                'commands': [],
                'pid': None,
            }
        
    def print_subprocess_output(self, result):
        """
        Helper function to print the output and error messages from a subprocess
        This is used to print the output of the command run in the run method
        """
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

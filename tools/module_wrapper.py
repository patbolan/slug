"""
Starting by writing this specifically for modules that operate on studies, not those
that work on subjects, projects, etc. Will get this working first then generalize.

Not supporting options yet, ither
"""
from tools.process_module_manager import ProcessModuleManager
from utils import get_data_folder, get_study_path, get_module_folder
import os
import subprocess
import json     
import shutil

class ModuleWrapper():
    def __init__(self, module_name=None, module_folder=None, module_script=None):
        self.name = module_name
        self.folder = module_folder
        self.script = module_script

        self.script_path = os.path.join(get_module_folder(), self.folder, self.script)
        if not os.path.isfile(self.script_path):    
            raise FileNotFoundError(f'Module script not found: {self.script_path}')     
        
        # Call the script and parse its output
        # Here, called once during initialization
        self.properties = self.get_script_properties() 

    def get_script_properties(self):
        """
        Runs the script at script_path with the command 'properties',
        captures its output, and parses it into a JSON object.
        """
        try:
            # Run the script with the parameter 'properties'
            result = subprocess.run(
                [self.script_path, "properties"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True  # Raises CalledProcessError if the command fails
            )

            # Log the standard output and errors
            if result.stdout:
                print(f"Script output:\n{result.stdout}")
            if result.stderr:
                print(f"Script errors:\n{result.stderr}")

            # Parse the output into a JSON object
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON output: {e}")
            raise
        
    def get_status_for_study(self, subject_name, study_name):
        """
        Calls the script with the command 'status' and properties '--target' and
         the study path.
        Captures its output and parses it into a JSON object.
        :param subject_name: The name of the subject.
        :param study_name: The name of the study.
        :return: JSON object containing the status information.
        """
        study_path = get_study_path(subject_name, study_name)
        if not study_path:
            raise FileNotFoundError(f"Study path not found for subject '{subject_name}' and study '{study_name}'")

        try:
            result = subprocess.run(
                [self.script_path, "status", "--target", study_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            if result.stdout:
                print(f"Script output:\n{result.stdout}")
            if result.stderr:
                print(f"Script errors:\n{result.stderr}")
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON output: {e}")
            raise                                              


    def get_context(self):
        return {
            'subject_name': self.subject_name,
            'study_name': self.study_name,
            'file_path': self.file_path,
        }

    # Note when overriding this method use "print" not loggers
    def run_command_line(self, command, target_path):
        print(f"Running {self.name} for target {target_path}")

        # Run the module, a command-line script
        cmd_line = [self.script_path, command, '--target', target_path] # Important: cmd is a list, not a string with spaces!
        print(f"***** Running module command line: {cmd_line}")

        # Run the command in a subprocess
        result = subprocess.run(
            cmd_line,   # Replace with your command and arguments
            capture_output=True,            # Captures both stdout and stderr
            text=True                       # Returns output as strings instead of bytes
        )
        # If you need the pid you can replace subprocess.run() with subprocess.Popen(), but 
        # it takes a little more code

        # Print the output and error messages
        self.print_subprocess_output(result)

    def run_in_subprocess(self):
        pm = ProcessModuleManager()
        ipid = pm.spawn_process(tool=self, command='run', mode='sync')
        print(f"Started asynchronous process for {self.name} with command 'run', ipid={ipid}")



    def is_undoable(self):
        return self.properties.get('undoable', False)



    def get_status_dict(self):
        """
        Returns a dictionary with the status of the tool.
        The status can be 'running', 'complete', 'available', or 'unavailable'.
        This dictionary is used by the UI to display the status of the tool and
        what commands can be run
        """
        pm = ProcessModuleManager()
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

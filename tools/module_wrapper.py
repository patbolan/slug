"""
Starting by writing this specifically for modules that operate on studies, not those
that work on subjects, projects, etc. Will get this working first then generalize.

Note that calling status for each  module is time consuming. I have print() calls
in place. Could optimize somehow, perhaps using "watchdog" to keep track of when 
studies are modified.

"""
from tools.process_module_manager import ProcessModuleManager
from utils import get_study_path, get_module_folder, get_data_folder, get_subject_path
import os
import subprocess
import json     
from flask import current_app
import time

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
            # if result.stdout:
            #     current_app.logger.debug(f"Script properties output:\n{result.stdout}")
            # if result.stderr:
            #     current_app.logger.debug(f"Script properties errors:\n{result.stderr}")

            # Parse the output into a JSON object
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Error running script: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Error parsing JSON output: {e}")
            raise
        
    def get_status(self, subject_name, study_name):
        """
        Calls the script with the command 'status' and properties '--target' and
         the study path.
        Captures its output and parses it into a JSON object.
        :param subject_name: The name of the subject.
        :param study_name: The name of the study.
        :return: JSON object containing the status information.
        """
        if subject_name is None:
            target_path = get_data_folder()
        elif study_name is None:
            target_path = get_subject_path(subject_name)
        else:
            target_path = get_study_path(subject_name, study_name)

        if not target_path:
            raise FileNotFoundError(f"Target path not found for subject '{subject_name}' and study '{study_name}'")

        try:
            # Measure time for subprocess execution
            subprocess_start = time.time()
            result = subprocess.run(
                [self.script_path, "status", "--target", target_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            current_app.logger.debug(f"Execution time for {self.name}/status: {time.time() - subprocess_start:.4f} seconds")

            #  Parse JSON
            status = json.loads(result.stdout)

            return status
        
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Error running script: {e.stderr}")
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Error parsing JSON output: {e}")

        json_str = '{"state": "error", "rationale": "Error retrieving status"}'
        return json.loads(json_str)                                              


    def get_context(self):
        return {
            'subject_name': self.subject_name,
            'study_name': self.study_name,
            'file_path': self.file_path,
        }

    # Note when overriding this method use "print" not loggers
    def run_command_line(self, command, target_path):
        current_app.logger.info(f"Running {self.name} for target {target_path}")

        # Run the module, a command-line script
        cmd_line = [self.script_path, command, '--target', target_path] # Important: cmd is a list, not a string with spaces!
        current_app.logger.info(f"Running module command line: {cmd_line}")

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
        current_app.logger.info(f"Started asynchronous process for {self.name} with command 'run', ipid={ipid}")


    def is_undoable(self):
        return self.properties.get('undoable', False)

        
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

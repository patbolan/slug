"""
ProcessManager Module

This module provides the `ProcessManager` class, which is responsible for 
managing the execution of tools in separate processes. It spawns new processes,
captures their output, and manages their lifecycle. It also maintains a record
of running and completed processes in designated folders.

Under the proces root folder, there are two folders, running and completed. 
New processes are created in the running folder, with a folder for each process
named using the OS's process id for that subprocess. Outputs from the process
are saved as files in that folder. WHen the process completes the process folder
is moved to the processes/completed folder. 

Key Features:
- Spawns new processes for tools and commands.
- Captures stdout and stderr of processes.
- Maintains process metadata in JSON files.
- Supports querying running and completed processes.
- Handles process cleanup and folder management.

Classes:
- ProcessManager: Manages the lifecycle of processes and provides utility 
methods for process management.

Dependencies:
- Python Standard Libraries: os, subprocess, shutil, glob, json, datetime, 
multiprocessing, sys, io, threading
- Custom Utilities: get_process_root_folder (from utils.py)

Author: Patrick Bolan
Date: Aug 2025
"""

from utils import get_process_root_folder
import os
import shutil
import json
from datetime import datetime
from multiprocessing import Process, Pipe
import subprocess
import sys
import io
import threading

""" 
ProcessModuleManager is responsible for managing the execution of tools in separate 
processes. It spawns new processes, captures their output, and manages their 
lifecycle. It also maintains a record of running and completed processes in 
designated folders. Note this class doesn't have meaningful state in this 
implementation.

With ProcessModuleManager instead of ProcessManager, the manager has more knowledge. 
The module is just an interface (wrapper) to the actual moduule, which is a command line script. 
The moduule and wrapper donn't know about the options and parameters
"""
class ProcessModuleManager():
    def __init__(self):
        self.process_root = get_process_root_folder()
        self.running_folder = os.path.join(self.process_root, 'running')
        self.completed_folder = os.path.join(self.process_root, 'completed')
        
        # Create folders if they don't exist
        if not os.path.exists(self.process_root):
            os.makedirs(self.process_root)
        if not os.path.exists(self.running_folder):
            os.makedirs(self.running_folder)
        if not os.path.exists(self.completed_folder):
            os.makedirs(self.completed_folder)



    def run_commandline(self, command_list, context_dict, blocking=True):
        """
        Run a command line command with captured output, time measurement, and postprocessing.
        Output files are written into a subdirectory named after the process id inside output_dir.
        The subdirectory is created immediately after Popen starts the process.

        Args:
            command_list (list): Command and arguments as list, e.g. ['ls', '-l']
            blocking (bool): If True, block until command completes.
                            If False, run in background thread.
            output_dir (str or None): Full path to folder where a subdirectory (named by pid) will be created
                                    to save stdout.txt, stderr.txt, and completion.json.
                                    If None, files are not written.

        Returns:
            If blocking: tuple (stdout, stderr, returncode, start_time, end_time, duration_seconds)
            If non-blocking: threading.Thread instance (command runs in background)
        """
        def _postprocess(stdout, stderr, returncode, start_time, end_time, pid):
            duration = (end_time - start_time).total_seconds()

            # Process dir is currently in running folder
            this_process_dir = os.path.join(self.running_folder, str(pid))
            os.makedirs(this_process_dir, exist_ok=True)

            with open(os.path.join(this_process_dir, 'stdout.txt'), 'w', encoding='utf-8') as f_out:
                f_out.write(stdout or "")

            with open(os.path.join(this_process_dir, 'stderr.txt'), 'w', encoding='utf-8') as f_err:
                f_err.write(stderr or "")

            completion_data = {
                "returncode": returncode,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration
            }
            with open(os.path.join(this_process_dir, 'completion.json'), 'w', encoding='utf-8') as f_json:
                json.dump(completion_data, f_json, indent=4)

            print(f"Command completed with return code {returncode} (pid {pid})")
            print(f"Started at: {start_time.isoformat()}")
            print(f"Ended at: {end_time.isoformat()}")
            print(f"Duration (seconds): {duration}")
            if stdout:
                print("Standard Output:")
                print(stdout)
            if stderr:
                print("Standard Error:")
                print(stderr)

            # Move the process folder to the completed folder   
            shutil.move(this_process_dir, self.completed_folder)
            print(f"Process folder moved to completed: {os.path.join(self.completed_folder, str(pid))}")    

        def _run():
            start_time = datetime.now()
            process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            pid = process.pid
            # Create output subdirectory immediately after starting process
            this_process_dir = os.path.join(self.running_folder, str(pid))
            os.makedirs(this_process_dir, exist_ok=True)

            # Write a context file. Add the start to context dict, stream that to json
            context_dict['start_time'] = start_time.isoformat()
            context_dict['name'] = f'slug:{context_dict["tool_name"]}:{context_dict["command"]}'
            with open(os.path.join(this_process_dir, 'context.json'), 'w') as json_file:
                json.dump(context_dict, json_file, indent=4)

            stdout, stderr = process.communicate()
            end_time = datetime.now()
            _postprocess(stdout, stderr, process.returncode, start_time, end_time, pid)
            return stdout, stderr, process.returncode, start_time, end_time, (end_time - start_time).total_seconds()

        if blocking:
            return _run()
        else:
            thread = threading.Thread(target=_run)
            thread.start()
            return thread


# Made obsolete with new refactoring
    # def spawn_process(self, tool, command, mode='async'):
    #     if not hasattr(tool, command):
    #         raise ValueError(f"Tool '{tool}' does not have command '{command}'")
    #     target = getattr(tool, command)
    #     if not callable(target):
    #         raise ValueError(f"Command '{command}' of tool '{tool}' is not callable")

    #     # Configure the new process
    #     context_dict = tool.get_context()
    #     process_name = f'slug:{tool.name}:{command}'

    #     # Create a new process
    #     print(f"Spawning process for {process_name} with command '{target.__name__}' on {context_dict}")
    #     parent_conn, child_conn = Pipe()
    #     process = Process(name=process_name, target=self.run_task_in_process, args=(tool, command, child_conn))
        
    #     process.start() # the .pid is not available until after this call
    #     print(f"   --> started pid={process.pid}, parent={os.getpid()}, {process.name}")

    #     # Set up a process folder for this process. 
    #     this_process_folder_name = f'{process.pid}'
    #     this_process_folder = os.path.join(self.running_folder, this_process_folder_name)        
    #     if not os.path.exists(this_process_folder):
    #         print(f'Creating process folder {this_process_folder}')
    #         os.makedirs(this_process_folder)

    #     # Write a context file
    #     datetime_start = datetime.now()
    #     timestamp_start = datetime_start.strftime('%Y-%m-%dT%H:%M:%S')
    #     process_context = {
    #         'name': process_name,
    #         'os_pid': process.pid,
    #         'subject_name': context_dict['subject_name'],
    #         'study_name': context_dict['study_name'],
    #         'file_path': context_dict['file_path'],
    #         'start_time': timestamp_start
    #     }    
    #     with open(os.path.join(this_process_folder, 'context.json'), 'w') as json_file:
    #         json.dump(process_context, json_file, indent=4)

    #     # configure tasks to run once the process completes
    #     def postprocess():
    #         stdout_data, stderr_data = parent_conn.recv() 
    #         process.join()
    #         retcode = process.exitcode
    #         print(f'The process pid={process.pid} completed with code {retcode}.')

    #         with open(os.path.join(this_process_folder, 'stdout.txt'), 'w') as f:
    #             f.write(stdout_data + '\n')

    #         # Only write stderr if there is any
    #         if stderr_data:
    #             with open(os.path.join(this_process_folder, 'stderr.txt'), 'w') as f:
    #                 f.write(stderr_data + '\n')
            
    #         datetime_end = datetime.now()
    #         timestamp_end = datetime_end.strftime('%Y-%m-%dT%H:%M:%S')
    #         completion_dict = {
    #             'return_code': retcode,
    #             'end_time': timestamp_end,
    #             'duration_s': f'{(datetime_end - datetime_start).total_seconds():.1f}',
    #         }
    #         with open(os.path.join(this_process_folder, 'completion.json'), 'w') as json_file:
    #             json.dump(completion_dict, json_file, indent=4)

    #         # Move the process folder to the completed folder   
    #         shutil.move(this_process_folder, self.completed_folder)
        
    #     watcher = threading.Thread(target=postprocess)
    #     watcher.start()
    #     print(f'Started a watcher thread to execute when pid={process.pid} terminates.')

    #     # If mode is 'sync', wait for the process to complete
    #     if mode == 'sync':
    #         process.join()

    #     return process.pid

    # Made obsolete with new refactoring
    # def run_task_in_process(self, tool_obj, method_name, conn):
    #     """    
    #     This function runs a task in a separate process and captures its stdout and stderr.
    #     """
              
    #     if not hasattr(tool_obj, method_name):
    #         raise ValueError(f"Tool '{tool_obj}' does not have command '{method_name}'")
    #     target = getattr(tool_obj, method_name)
    #     if not callable(target):
    #         raise ValueError(f"Command '{method_name}' of tool '{tool_obj}' is not callable")

    #     # Redirect stdout and stderr within this process
    #     stdout_buffer = io.StringIO()
    #     stderr_buffer = io.StringIO()
    #     sys.stdout = stdout_buffer
    #     sys.stderr = stderr_buffer

    #     try:
    #         target()
    #     except Exception as e:
    #         print(f"Exception in run: {e}", file=sys.stderr)
    #     finally:
    #         # Restore stdout/stderr and send output back
    #         sys.stdout = sys.__stdout__
    #         sys.stderr = sys.__stderr__
    #         conn.send((stdout_buffer.getvalue(), stderr_buffer.getvalue()))
    #         conn.close()


    def get_process_id(self, subject_name, study_name, tool_name):
        """
        Search for a process by subject_name, study_name, and tool_name
        Returns the pid of the most recent process if found, otherwise None.
        """
        for folder_type in ['running', 'completed']:
            processes = self.get_process_dicts(folder_type=folder_type, sort_order='most_recent')

            for process_info in processes:  
                if (process_info['subject_name'] == subject_name and
                    process_info['study_name'] == study_name and
                    process_info['name'].startswith(f'slug:{tool_name}')):
                    return process_info['pid']
        return None
                    
    def is_running(self, pid):
        process_info = self.get_process_dict(pid)
        if process_info is not None and ('status' in process_info) and process_info['status'] == 'running': 
            return True
        else:
            return False

    def get_process_dict(self, pid):
        """
        Returns a dictionary representing the process with the given pid.
        The dictionary includes name, pid, subject_name, study_name, command, start_time,
        return_code, end_time, and duration_s.
        If no such process is found, returns None.
        """
        if pid is None:
            return None

        # First look in running, then completed
        process_folder = os.path.join(self.running_folder, str(pid))        
        if os.path.isdir(process_folder):
            status = 'running'
        else:        
            process_folder = os.path.join(self.completed_folder, str(pid))
            if os.path.isdir(process_folder): 
                status = 'completed' 
            else:
                return None       
        print(f'For pid {pid}, found in folder {status}')

        context_file = os.path.join(process_folder, 'context.json')
        completion_file = os.path.join(process_folder, 'completion.json')
        process_info = dict() # Start with empty dict

        try:
            with open(context_file, 'r') as json_file:
                process_context = json.load(json_file)
                process_info = {
                    'name': process_context.get('name', 'N/A'),
                    'status': status,
                    'pid': pid,
                    'subject_name': process_context.get('subject_name', 'N/A'),
                    'study_name': process_context.get('study_name', 'N/A'),
                    'start_time': process_context.get('start_time', 'N/A'),
                }
        except Exception as e:
            print(f"Error reading context.json in {process_folder}: {e}")
            #return None

        # If the process is completed, add completion details
        try:
            with open(completion_file, 'r') as json_file:
                completion_context = json.load(json_file)
                process_info['returncode'] = completion_context.get('returncode', 'N/A')
                process_info['start_time'] = completion_context.get('start_time', 'N/A')
                process_info['end_time'] = completion_context.get('end_time', 'N/A')
                process_info['duration'] = completion_context.get('duration', 'N/A')
        except FileNotFoundError:
            # If completion file does not exist, it means the process is still running
            process_info['returncode'] = ''
            #process_info['start_time'] = '' # Dont overwrite this
            process_info['end_time'] = ''
            process_info['duration'] = ''
            

        return process_info

    def get_process_dicts(self, folder_type='running', sort_order='most_recent'):
        """
        Returns a list of dictionaries representing all processes in the specified folder.
        Each dictionary includes name, pid, subject_name, study_name, command, and start-time.
        :param folder_type: Either 'running' or 'completed' to specify which folder to look in.
        """
        if folder_type == 'running':
            folder_path = self.running_folder
        elif folder_type == 'completed':
            folder_path = self.completed_folder
        else:
            raise ValueError("Invalid folder_type. Must be 'running' or 'completed'.")

        processes = []
        for folder_name in os.listdir(folder_path):
            processes.append( self.get_process_dict(folder_name) )

        print(f'Found {len(processes)} processes in {folder_type} folder: {processes}')

        if processes:
            if sort_order == 'most_recent':
                # Sort processes by most recent start_time  
                processes = sorted(processes, key=lambda x: x['start_time'], reverse=True)
            else:
                # Sort processes by oldest start_time
                processes = sorted(processes, key=lambda x: x['start_time'])  
            pass

        return processes
    
    def clear_logs(self, folder_type='running'):
        """
        Clears the logs of all processes in the specified folder.
        :param folder_type: Either 'running' or 'completed' to specify which folder to clear.
        """
        if folder_type == 'running':
            folder_path = self.running_folder
        elif folder_type == 'completed':
            folder_path = self.completed_folder
        else:
            raise ValueError("Invalid folder_type. Must be 'running' or 'completed'.")

        for process_folder in os.listdir(folder_path):
            process_folder_path = os.path.join(folder_path, process_folder)
            if os.path.isdir(process_folder_path):
                shutil.rmtree(process_folder_path)
                print(f"Deleted folder: {process_folder_path}")




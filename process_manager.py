from utils import get_study_file_path, get_study_path, get_process_root_folder
import os
import subprocess
import shutil
import glob
import json
from datetime import datetime
from multiprocessing import Process, Pipe
import sys
import io
import threading


# ProcessManager is responsible for managing the execution of tools in separate processes.
# It spawns new processes, captures their output, and manages their lifecycle.
# It also maintains a record of running and completed processes in designated folders.
# Note this doesn't have meaningful state in this implementation.
class ProcessManager():
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


    def spawn_process(self, tool, command):
        if not hasattr(tool, command):
            raise ValueError(f"Tool '{tool}' does not have command '{command}'")
        target = getattr(tool, command)
        if not callable(target):
            raise ValueError(f"Command '{command}' of tool '{tool}' is not callable")

        # Configure the new process
        context_dict = tool.get_context()
        process_name = f'slug:{tool.name}:{command}'

        # Create a new process
        print(f"Spawning process for {process_name} with command '{target.__name__}' on {context_dict}")
        parent_conn, child_conn = Pipe()
        process = Process(name=process_name, target=self.run_task_in_process, args=(tool, command, child_conn))
        
        process.start() # the .pid is not available until after this call
        print(f"   --> started pid={process.pid}, parent={os.getpid()}, {process.name}")

        # Set up a process folder for this process. 
        this_process_folder_name = f'{process.pid}'
        this_process_folder = os.path.join(self.running_folder, this_process_folder_name)        
        if not os.path.exists(this_process_folder):
            print(f'Creating process folder {this_process_folder}')
            os.makedirs(this_process_folder)

        # Write a context file
        datetime_start = datetime.now()
        timestamp_start = datetime_start.strftime('%Y-%m-%dT%H:%M:%S')
        process_context = {
            'name': process_name,
            'os_pid': process.pid,
            'subject_name': context_dict['subject_name'],
            'study_name': context_dict['study_name'],
            'file_path': context_dict['file_path'],
            'start_time': timestamp_start
        }    
        with open(os.path.join(this_process_folder, 'context.json'), 'w') as json_file:
            json.dump(process_context, json_file, indent=4)

        # configure tasks to run once the process completes
        def postprocess():
            stdout_data, stderr_data = parent_conn.recv() 
            process.join()
            retcode = process.exitcode
            print(f'The process pid={process.pid} completed with code {retcode}.')

            with open(os.path.join(this_process_folder, 'stdout.txt'), 'w') as f:
                f.write(stdout_data + '\n')

            # Only write stderr if there is any
            if stderr_data:
                with open(os.path.join(this_process_folder, 'stderr.txt'), 'w') as f:
                    f.write(stderr_data + '\n')
            
            datetime_end = datetime.now()
            timestamp_end = datetime_end.strftime('%Y-%m-%dT%H:%M:%S')
            completion_dict = {
                'return_code': retcode,
                'end_time': timestamp_end,
                'duration_s': f'{(datetime_end - datetime_start).total_seconds():.1f}',
            }
            with open(os.path.join(this_process_folder, 'completion.json'), 'w') as json_file:
                json.dump(completion_dict, json_file, indent=4)


            # Move the process folder to the completed folder   
            shutil.move(this_process_folder, self.completed_folder)
        
        watcher = threading.Thread(target=postprocess)
        watcher.start()
        print(f'Started a watcher thread to execute when pid={process.pid} terminates.')

        return process.pid

    # This function runs a task in a separate process and captures its stdout and stderr.
    def run_task_in_process(self, tool_obj, method_name, conn):

        if not hasattr(tool_obj, method_name):
            raise ValueError(f"Tool '{tool_obj}' does not have command '{method_name}'")
        target = getattr(tool_obj, method_name)
        if not callable(target):
            raise ValueError(f"Command '{method_name}' of tool '{tool_obj}' is not callable")

        # Redirect stdout and stderr within this process
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer

        try:
            target()
        except Exception as e:
            print(f"Exception in run: {e}", file=sys.stderr)
        finally:
            # Restore stdout/stderr and send output back
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            conn.send((stdout_buffer.getvalue(), stderr_buffer.getvalue()))
            conn.close()

    # Search for a process by subject_name, study_name, and tool_name
    # Returns the pid of the process if found, otherwise None.
    def get_process_id(self, subject_name, study_name, tool_name):

        for folder_type in ['running', 'completed']:
            processes = self.get_processes(folder_type=folder_type)
            for process_info in processes:  
                if (process_info['subject_name'] == subject_name and
                    process_info['study_name'] == study_name and
                    process_info['name'].startswith(f'slug:{tool_name}')):
                    return process_info['pid']
        return None
                    
    def is_running(self, pid):
        process_info = self.get_process_info(pid)
        if process_info is not None and ('status' in process_info) and process_info['status'] == 'running': 
            return True
        else:
            return False

    def get_process_info(self, pid):
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
                    'file_path': process_context.get('file_path', 'N/A'),
                    'start_time': process_context.get('start_time', 'N/A')
                }
        except Exception as e:
            print(f"Error reading context.json in {process_folder}: {e}")
            return None

        # If the process is completed, add completion details
        try:
            with open(completion_file, 'r') as json_file:
                completion_context = json.load(json_file)
                process_info['return_code'] = completion_context.get('return_code', 'N/A')
                process_info['end_time'] = completion_context.get('end_time', 'N/A')
                process_info['duration_s'] = completion_context.get('duration_s', 'N/A')
        except FileNotFoundError:
            # If completion file does not exist, it means the process is still running
            process_info['return_code'] = ''
            process_info['end_time'] = ''
            process_info['duration_s'] = ''

        return process_info

    def get_processes(self, folder_type='running'):
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
            processes.append( self.get_process_info(folder_name) )

        # Sort processes by most recent start_time  
        processes = sorted(processes, key=lambda x: x['start_time'], reverse=True)  
        return processes




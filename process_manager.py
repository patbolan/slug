from utils import get_study_file_path, get_study_path, get_process_root_folder
import os
import subprocess
import shutil
import glob
import json
from datetime import datetime
from multiprocessing import Process


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
        name = f'slug-{tool.__name__}-{command}'
        if not callable(target):
            raise ValueError(f"Command '{command}' of tool '{tool}' is not callable")
        
        # Create a new process
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        print(f"Spawning process for {name} with target '{target.__name__}' at time {timestamp}")
        this_process_folder_name = f'{timestamp}'
        this_process_folder = os.path.join(self.running_folder, this_process_folder_name)
        if not os.path.exists(this_process_folder):
            os.makedirs(this_process_folder)

        context_dict = tool.get_context()

        process = Process(name=name, target=target)
        process.start()
        print(f"Spawning process for {name} with command '{target.__name__}' on {context_dict}")
        pid = os.getpid()
        print(f"pid={process.pid}, parent={pid}, {process.name}")

        process_context = {
            'name': name,
            'pid': pid,
            'subject-name': context_dict['subject-name'],
            'study-name': context_dict['study-name'],
            'file-path': context_dict['file-path'],
            'command': '???',
            'start-time': timestamp
        }    
        with open(os.path.join(this_process_folder, 'context.json'), 'w') as json_file:
            json.dump(process_context, json_file, indent=4)


    # For testing
    def create_dummy_process(self):

        # One in running first
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        this_process_folder_name = f'{timestamp}'
        this_process_folder = os.path.join(self.running_folder, this_process_folder_name)
        print(f'Creating Dummy process {this_process_folder}')
        if not os.path.exists(this_process_folder):
            os.makedirs(this_process_folder)

        process_context = {
            'name': 'tmp-process',
            'pid': 42,
            'subject-name': 'PJB-0001',
            'study-name': '', 
            'command': '/here/is/my/command.sh',
            'start-time': timestamp
        }    
        with open(os.path.join(this_process_folder, 'context.json'), 'w') as json_file:
            json.dump(process_context, json_file, indent=4)

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
            process_folder = os.path.join(folder_path, folder_name)
            context_file = os.path.join(process_folder, 'context.json')

            if os.path.isdir(process_folder) and os.path.isfile(context_file):
                try:
                    with open(context_file, 'r') as json_file:
                        process_context = json.load(json_file)
                        processes.append({
                            'name': process_context.get('name', 'N/A'),
                            'pid': process_context.get('pid', 'N/A'),
                            'subject_name': process_context.get('subject-name', 'N/A'),
                            'study_name': process_context.get('study-name', 'N/A'),
                            'command': process_context.get('command', 'N/A'),
                            'start_time': process_context.get('start-time', 'N/A')
                        })
                except Exception as e:
                    print(f"Error reading context.json in {process_folder}: {e}")
        return processes




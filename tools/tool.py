from abc import ABC
from tools.process_manager import ProcessManager

class Tool(ABC):
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

    def output_files_exist(self):
        raise NotImplementedError("Subclasses should implement this method")

    def input_files_exist(self):
        return True

    def get_status_dict(self):
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
        elif self.output_files_exist():
            return {
                'name': self.name,
                'status': 'complete',
                'message': f'{self.name} has run successfully',
                'commands': ['undo'] if self.is_undoable() else [],
                'pid': None,
            }
        elif self.input_files_exist():
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
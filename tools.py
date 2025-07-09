from utils import *
import os


def get_tools_for_study(subject_name, study_name):

    # returns a list of tools
    # HARDWIRED
    # toolset = [ 
    #     {'name': 'NiiConverter', 'status': 'complete', 'commands':['undo'] }, 
    #     {'name': 'T2Mapping', 'status': 'available', 'commands':['run'] }, 
    #     {'name': 'Segmentation', 'status': 'unavailable', 'message':'Not yet implemented', 'commands':[] }, 
    # ]

    nii_converter = NiiConverter(subject_name, study_name)  
    toolset = [nii_converter.get_descriptor()]

    return toolset


class NiiConverter:
    def __init__(self, subject_name, study_name):
        self.subject_name = subject_name
        self.study_name = study_name

    # returns status, message
    def get_status(self):
        # Check for nii-original
        nii_original_path = get_study_file_path(self.subject_name, self.study_name, 'nii-original')
        dicom_original_path = get_study_file_path(self.subject_name, self.study_name, 'dicom-original')
        if os.path.exists(nii_original_path):
            return 'complete', ''
        else:
            # Check for pre-reqs
            if os.path.exists(dicom_original_path):
                return 'available', ''
            else:
                return 'unavailable', 'dicom-original not found.'
            
    def get_commands(self):
        status, message = self.get_status()
        if status == 'complete':
            return ['undo']
        elif status == 'available':
            return ['run']
        else:
            return []   
    
    def get_descriptor(self):
        status, message = self.get_status()
        descriptor_dict = {'name': 'NiiConverter',
                           'status': status,
                           'message': message,
                           'commands': self.get_commands()}
        return descriptor_dict






import os
import pydicom 
import glob
import shutil
from .tool import Tool
from utils import get_study_file_path


# A tool for finding special Dicom Raw Storage files and removing them from the dicom-original folder tree
# In some Philips datasets there is a Raw Storage file, SOP Class UID = 1.2.840.10008.5.1.4.1.1.66. 
# The presence of htis file probably depends on how the data were exported.
# This function will look through all the dicom-original folders looking
# for these raw data files, determined by their SOPClassUID. If any are
# found they are moved to a folder called dicom-raw-storatge, because these will break all the
# other tools.
#
# This tool will create the dicom-raw-storage folder if it does not exist regardless of whether it finds any files, 
# just so you can tell that the tool has run.
class DicomRawStorageCleaner(Tool):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'dicom-raw-storage-cleaner'
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        
        # don't create the raw storage folder here, it will be created in the run method if needed
        self.dicom_raw_storage_path = get_study_file_path(subject_name, study_name, 'dicom-raw-storage')

    def output_files_exist(self):
        # Check for the dicom-raw-storage folder
        return os.path.isdir(self.dicom_raw_storage_path)

    def input_files_exist(self):
        # Check if the dicom-original folder exists. Don't look for contents, just the folder
        return os.path.isdir(self.dicom_original_path)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Create the raw storage folder if it does not exist
        if not os.path.exists(self.dicom_raw_storage_path):
            os.makedirs(self.dicom_raw_storage_path)

        # Look at all files in the dicom-original folder recursively
        dicom_files = [f for f in glob.glob(os.path.join(self.dicom_original_path, '**'), recursive=True) if os.path.isfile(f)]

        print(f"Found {len(dicom_files)} DICOM files in {self.dicom_original_path}. Searching for raw storage files...")        
        raw_storage_files = []
        for dicom_file in dicom_files:  
            print(f'Checking DICOM file: {dicom_file}')
            try:
                dicom_data = pydicom.dcmread(dicom_file, stop_before_pixels=True)
                print(f'  DICOM file {dicom_file} SOPClassUID: {dicom_data.SOPClassUID}')
                if dicom_data.SOPClassUID == '1.2.840.10008.5.1.4.1.1.66':
                    raw_storage_files.append(dicom_file)
                    print(f"Found raw storage file: {dicom_file}")
            except Exception as e:
                print(f"Error reading DICOM file {dicom_file}: {e}")    
        
        if not raw_storage_files:   
            print(f"No raw storage files found in {self.dicom_original_path}. Nothing to do.")
        else:   
            print(f"Found {len(raw_storage_files)} raw storage files. Moving them to {self.dicom_raw_storage_path}...")

            # Move the raw storage files to the raw storage folder
            for raw_file in raw_storage_files:
                shutil.move(raw_file, self.dicom_raw_storage_path)
                print(f"Moved {raw_file} to {self.dicom_raw_storage_path}")

    def is_undoable(self):
        return False

    def undo(self):
        raise NotImplementedError(f"{self.name} does not support undo. Need to do this manually.")
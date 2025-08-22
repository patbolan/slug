"""
ParseDicomFolder Tool

This tool is a wrapper aroudn the parse_dicom_folder() function, which has been converted 
from Matlab code. 

When createing a new file, the raw dicom can be put into a folder called `dicom-raw` and 
this tool will parse it, copying the files to a new folder called `dicom-original`, using
naming conventions suppported by this project. Very similar to EJA's  modified dcmtk 
receiver with human-readable names (thanks Eddie!)
"""
import os
import re
import shutil
import pydicom
from .tool_base import ToolBase
from utils import get_study_file_path



class ParseDicomFolder(ToolBase):
    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'parse-dicom-folder'
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        
        # don't create the raw storage folder here, it will be created in the run method 
        self.dicom_raw = get_study_file_path(subject_name, study_name, 'dicom-raw')

    def are_output_files_present(self):
        # A little strange, but we'll always say false. Can't tell if the dicom-original folder 
        # was created manually or by this tool.
        #return os.path.isdir(self.dicom_original_path)
        return False

    def are_input_files_present(self):
        # Check if the dicom-original folder exists. Don't look for contents, just the folder
        return os.path.isdir(self.dicom_raw)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Create dicom-original if it does not exist
        if not os.path.exists(self.dicom_original_path):
            os.makedirs(self.dicom_original_path)
        parse_dicom_folder(self.dicom_raw, targetdir=self.dicom_original_path)

    def is_undoable(self):      
        return False

    def undo(self):
        """ 
        If a dicom-raw folder exists, then you can delete the dicom-original folder.
        """
        if os.path.exists(self.dicom_raw):
            shutil.rmtree(self.dicom_original_path)



def parse_dicom_folder(dirname, targetdir=None):
    """
    Parse a folder for DICOM files, print tags, and optionally copy them to a new target directory 
    in a human-readable hierarchical format.

    This function lists all the files in a directory and lists some of the
    dicom tags. If a targetdir is provided, it will copy all those files to a
    new area using a human-readable hierarchical file format.

    This version is updated to support GE, where teh series numbers can be
    up to 100k. Also not using ST001 in file and folder names
    Also adding acquisition numbers    
    """

    # Recursively get all files
    filelist = []
    for root, _, files in os.walk(dirname):
        for f in files:
            if f not in ['.', '..', '.DS_Store']:
                filelist.append(os.path.join(root, f))

    print(f"Found {len(filelist)} files.")

    # Determine if we should copy
    bCopy = targetdir is not None
    if bCopy:
        print(f"Copying files to human-readable form in {targetdir}")
        os.makedirs(targetdir, exist_ok=True)
    else:
        print("No target specified, just printing")

    # Process each file
    for idx, fname in enumerate(filelist, start=1):
        if not is_dicom(fname):
            print(f"{idx},{os.path.basename(fname)}, not-dicom")
            continue

        hdr = pydicom.dcmread(fname, stop_before_pixels=True)
        sequence_name = get_field_if_exists(hdr, 'SequenceName')
        series_description = get_field_if_exists(hdr, 'SeriesDescription')

        if bCopy:
            series_number = int(get_field_if_exists(hdr, 'SeriesNumber', 0))
            seriesdirname = f"MR-SE{series_number:05d}-{series_description}"
            seriesdirname = legalize_filename(seriesdirname)

            seriesdirpath = os.path.join(targetdir, seriesdirname)
            os.makedirs(seriesdirpath, exist_ok=True)

            acq_number = int(get_field_if_exists(hdr, 'AcquisitionNumber', 1))
            inst_number = int(get_field_if_exists(hdr, 'InstanceNumber', 0))

            targetfname = os.path.join(
                seriesdirpath,
                f"MR-SE{series_number:05d}-{acq_number:04d}-{inst_number:04d}.dcm"
            )

            if os.path.exists(targetfname):
                raise FileExistsError(f"Target file already exists: {targetfname}")
            if inst_number >= 10000:
                raise ValueError(f"InstanceNumber too large: {inst_number}")

            print(targetfname)
            shutil.copy2(fname, targetfname)
        else:
            series_number = get_field_if_exists(hdr, 'SeriesNumber', 0)
            acq_number = get_field_if_exists(hdr, 'AcquisitionNumber', 1)
            inst_number = get_field_if_exists(hdr, 'InstanceNumber', 0)
            print(f"{idx} <{os.path.basename(fname)}>, "
                  f"({series_number},{acq_number},{inst_number}), "
                  f"{series_description}, sequence = '{sequence_name}'")


def is_dicom(fname):
    """Check if a file is a DICOM file by attempting to read its header."""
    try:
        pydicom.dcmread(fname, stop_before_pixels=True)
        return True
    except Exception:
        return False


def get_field_if_exists(hdr, fieldname, default=''):
    """Get a DICOM tag if it exists, otherwise return a default value."""
    return getattr(hdr, fieldname, default)


def legalize_filename(oldfname):
    """Replace illegal characters in filenames with underscores."""
    # Allow alphanumeric, -, _, ., (), [], :
    return re.sub(r'[^a-zA-Z0-9\-\_\.\(\)\[\]:]', '_', str(oldfname))

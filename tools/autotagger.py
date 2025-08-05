"""
AutoTagger Tool
This tool look at the dicom series name and manufacturer string to figure out what 
type of data it is. This is crude, ad-hoc logic, really just a time saver. The user
will likely need to modify the tags due to repeated scans, non-standard naming, etc.
The results of the tagging are saved in the dicom_tags.csv file, which can then be
manually edited. 

Disable the undo feature for production - it is useful for testing but will clobber
any manual edits.

If needed this logic can be extended to use more header information and make better
choices. Right now it just uses the series description and manufacturer.
"""

from .tool_base import ToolBase
import os
from utils import get_study_file_path, get_study_path, get_sample_dicom_header, get_series_number_from_folder
import tempfile
import glob

# Implements logic for identifying dicom series, applying tags, and storing them in the dicom_tags.csv file
class AutoTagger(ToolBase):

    def __init__(self, subject_name, study_name):
        super().__init__(subject_name, study_name)
        self.name = 'autotagger'

        # Specify the test file path and dicom folder
        self.tag_file = os.path.join(get_study_file_path(self.subject_name, self.study_name, 'dicom_tags.csv'))
        self.dicom_original_path = get_study_file_path(subject_name, study_name, 'dicom-original')
        self.study_folder = get_study_path(subject_name, study_name)

    def are_input_files_present(self):
        return os.path.isdir(self.dicom_original_path)
    
    def are_output_files_present(self):
        return os.path.isfile(self.tag_file)

    def run(self):
        print(f"Running {self.name} for subject {self.subject_name} and study {self.study_name}")

        # Get a list of dicom series folders
        series_folders = [f for f in glob.glob(os.path.join(self.dicom_original_path, '**'), recursive=True) if os.path.isdir(f)]
        series_folders.sort()

        # Create the dicom_tags.csv file (it should not exist already)
        assert not os.path.isfile(self.tag_file), f"Tag file {self.tag_file} already exists. Should not happen."

        # I write to a temporary file first, then move it to the final location to prevent other processses 
        # reading a half-written file. Note I write the temp file in the study folder so it can be copied. If 
        # you write it in /tmp, then os.replace() can fail since its on a different filesystem.
        with tempfile.NamedTemporaryFile('w', dir=self.study_folder, delete=False) as tf:
            tempname = tf.name
            tf.write(f'seriesnum,tag\n')
            for series_folder in series_folders:
                series_name = os.path.basename(series_folder)
                series_number = get_series_number_from_folder(series_name)
                if series_number is None:
                    print(f"Skipping folder {series_name} as it does not have a valid series number")
                    continue

                hdr = get_sample_dicom_header(self.subject_name, self.study_name, series_name)
                manufacturer = hdr.get('Manufacturer', 'Unknown') if hdr else 'Unknown'

                print(f"Processing series {series_number} with name '{series_name}' and manufacturer '{manufacturer}'")
                
                # Guess the tag from the series name and manufacturer
                tag = self.guess_tag_from_seriesname(series_name, manufacturer)
                if tag:
                    tf.write(f'{series_number},{tag}\n')
                    print(f"Tagged series {series_number} with tag '{tag}'")
                else:
                    tf.write(f'{series_number},\n')
                    print(f"No tag found for series {series_number} with name '{series_name}' and manufacturer '{manufacturer}'")
        
        # Now move the temporary file to the final tag file location
        os.replace(tempname, self.tag_file)

    # Disable this undo - I don't want to delete the tags file so easily
    def is_undoable(self):
        return False
    
    def undo(self):
        print(f"Undoing {self.name} for subject {self.subject_name} and study {self.study_name}")
        if os.path.isfile(self.tag_file):
            os.remove(self.tag_file)


    # Direct conversion from matlab
    def guess_tag_from_seriesname(self, series_name, manufacturer):
        # Helper for case-insensitive substring search
        def ci_contains(haystack, needle):
            return needle.lower() in haystack.lower()
        
        # Set manufacturer variable
        manufact = ''
        if ci_contains(manufacturer, 'SIEMENS'):
            manufact = 'Siemens'
        elif ci_contains(manufacturer, 'Philips'):
            manufact = 'Philips'
        elif ci_contains(manufacturer, 'GE'):
            manufact = 'GE'
        
        series = ''
        
        # Siemens matching
        if ci_contains(manufacturer, 'SIEMENS'):
            manufact = 'Siemens'
            if ci_contains(series_name, 'b1map-6iso'):
                series = 'b1map'
            elif ci_contains(series_name, 'b1map'):
                series = 'b1map_x2'
            elif ci_contains(series_name, 't2_ana_axial'):
                series = 't2_ref'
            elif ci_contains(series_name, 'axial_1x1x1'):
                series = 'template'
            elif ci_contains(series_name, 'gre-axial'):
                series = 'thermo'
            elif ci_contains(series_name, 'vfa'):
                series = 't1_vfa'
            elif ci_contains(series_name, 'post_pelvis'):
                series = 't1_post'
            elif ci_contains(series_name, 'dynamic_sub'):
                series = 'dce_sub'
            elif ci_contains(series_name, 'dynamic'):
                series = 'dce_source'
            elif ci_contains(series_name, 'vibe'):
                series = 't1_vfa2'
            elif ci_contains(series_name, 'tse-ir'):
                series = 't1_tse'
            elif ci_contains(series_name, 'tfl_ti'):
                series = 't1_tfl'
            elif (ci_contains(series_name, 'semc') or ci_contains(series_name, 'se_mc')) and ci_contains(series_name, 'original'):
                series = 't2_semc2'
            elif (ci_contains(series_name, 'semc') or ci_contains(series_name, 'se_mc')) and ci_contains(series_name, '1x1x5'):
                series = 't2_semc'
            elif ci_contains(series_name, 't2map') or ci_contains(series_name, 't2_map'):
                series = 't2_semc'
            elif ci_contains(series_name, 'te101'):
                series = 't2_ref'
            elif ci_contains(series_name, 't2_tse_ax'):
                series = 't2_tse'
            elif ci_contains(series_name, 'b1600'):
                series = 'dwi_highb'
            elif ci_contains(series_name, 'space'):
                series = 't2_3d'
            elif ci_contains(series_name, '_trace') and ci_contains(series_name, 'zoomit'):
                series = 'dwi_source2'
            elif ci_contains(series_name, 'adc') and ci_contains(series_name, 'zoomit'):
                series = 'dwi_adc2'
            elif ci_contains(series_name, '_calc') and ci_contains(series_name, 'zoomit'):
                series = 'dwi_calc2'
            elif ci_contains(series_name, '_trace') and ci_contains(series_name, '-notzoomit'):
                series = 'dwi_source'
            elif ci_contains(series_name, 'adc') and ci_contains(series_name, '-notzoomit'):
                series = 'dwi_adc'
            elif ci_contains(series_name, '_calc') and ci_contains(series_name, '-notzoomit'):
                series = 'dwi_calc'
            else:
                series = ''
                manufact = ''
        
        # GE matching
        if ci_contains(manufacturer, 'GE'):
            manufact = 'GE'
            if ci_contains(series_name, 'b1map-optimized_rfdrive'):
                series = 'b1map'
            elif ci_contains(series_name, 'b1map-preset'):
                series = 'b1map_x2'
            elif ci_contains(series_name, 'b1map-quadrature'):
                series = 'b1map_x3'
            elif ci_contains(series_name, 'GRE-Axial_1x1x1') or ci_contains(series_name, 'Ax-1mm'):
                series = 'template'
            elif ci_contains(series_name, 'te_108') and not ci_contains(series_name, 'R_squared'):
                series = 't2_ref'
            elif ci_contains(series_name, 'tempmap'):
                series = 'thermo'
            elif ci_contains(series_name, 't1_vfa'):
                series = 't1_vfa'
            elif ci_contains(series_name, 'dce_flip'):
                series = 't1_vfa2'
            elif ci_contains(series_name, 'disco'):
                series = 't1_vfa2'
            elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR40')):
                series = 't1_smart1_hr40'
            elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR40')):
                series = 't1_smart1_hr40_raw'
            elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'T1_map[') and not ci_contains(series_name, 'orig') and ci_contains(series_name, 'HR70')):
                series = 't1_smart1_hr70'
            elif (ci_contains(series_name, 'smart1') and ci_contains(series_name, 'loc') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig') and not ci_contains(series_name, 'T1_map[') and ci_contains(series_name, 'HR70')):
                series = 't1_smart1_hr70_raw'
            elif ci_contains(series_name, 'fse_ir') and not ci_contains(series_name, 'R_squared'):
                series = 't1_tse'
            elif ci_contains(series_name, 'T2map') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig'):
                series = 't2_semc2'
            elif ci_contains(series_name, 'T2map') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig'):
                series = 't2_semc2_raw'
            elif ci_contains(series_name, 'pros_ax_t2') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'orig'):
                series = 't2_tse'
            elif ci_contains(series_name, 'pros_ax_t2') and not ci_contains(series_name, 'R_squared') and ci_contains(series_name, 'orig'):
                series = 't2_tse_raw'
            elif ci_contains(series_name, 'b1600'):
                series = 'dwi_highb'
            elif ci_contains(series_name, '3d_t2'):
                series = 't2_3d'
            elif ci_contains(series_name, 'dynamic'):
                series = 'dce_source'
            elif ci_contains(series_name, 'dynamic_sub'):
                series = 'dce_sub'
            elif ci_contains(series_name, 'post_pelvis'):
                series = 't1_post'
            elif ci_contains(series_name, 'dwi_b600') and not ci_contains(series_name, 'R_squared'):
                series = 'dwi_source'
            elif ci_contains(series_name, 'focus_b50_800') and not ci_contains(series_name, 'R_squared') and not ci_contains(series_name, 'synthetic'):
                series = 'dwi_source2'
            elif ci_contains(series_name, 'dwi_b1000') and not ci_contains(series_name, 'synthetic'):
                series = 'dwi_source2_x2'
            else:
                series = ''
                manufact = ''
        
        # Philips matching
        if ci_contains(manufacturer, 'PHILIPS'):
            manufact = 'philips'
            if ci_contains(series_name, 'b1map'):
                series = 'b1map'
            elif ci_contains(series_name, 'te108'):
                series = 't2_ref'
            elif ci_contains(series_name, 't2w_tra_clin'):
                series = 't2_tse'
            elif ci_contains(series_name, 'thrive-match'):
                series = 'thermo'
            elif ci_contains(series_name, 'thrive-hires'):
                series = 'template'
            elif ci_contains(series_name, 'TVFA'):
                series = 't1_vfa_x2'
            elif ci_contains(series_name, 'mDIXON'):
                series = 't1_vfa2'
            elif ci_contains(series_name, 'IR_TSE'):
                series = 't1_tse'
            elif ci_contains(series_name, 'IRTFE'):
                series = 't1_tfl'
            elif ci_contains(series_name, '11echoes'):
                series = 't2_semc2'
            elif ci_contains(series_name, '32echoes'):
                series = 't2_semc'
            elif ci_contains(series_name, 'b1600'):
                series = 'dwi_highb'
            elif ci_contains(series_name, '3D_T2'):
                series = 't2_3d'
            elif ci_contains(series_name, 'post_pelvis'):
                series = 't1_post'
            elif ci_contains(series_name, '-Reg_-_DWI'):
                series = 'dwi_source2'
            elif ci_contains(series_name, '-dRegDWI'):
                series = 'dwi_adc2'
            elif ci_contains(series_name, '-eRegDWI'):
                series = 'dwi_calc2'
            else:
                series = ''
                manufact = ''
        
        tag = series
        return tag

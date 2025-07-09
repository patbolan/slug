import os
import re

DATA_DIR = '/home/bakken-raid8/pcad2/data'

def get_all_subjects():
    pattern = re.compile(r'^[A-Z]{3}-\d{4}$')  # Pattern for XXX-0000
    subjects = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d)) and pattern.match(d)]
    subjects.sort()
    return subjects

def get_studies_for_subject(subject_name):
    subject_path = get_subject_path(subject_name)
    if not os.path.isdir(subject_path):
        return []
    pattern = re.compile(r'MR-\d{8}$')  # Pattern for MR-YYYYMMDD
    studies = [d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d)) and pattern.match(d)]
    studies.sort()
    return studies

def get_subject_path(subject_name):
    subject_path = os.path.join(DATA_DIR, subject_name)
    if not os.path.isdir(subject_path):
        return None
    return subject_path

def get_study_path(subject_name, study_name):
    subject_path = get_subject_path(subject_name)
    if not subject_path:
        return None
    study_path = os.path.join(subject_path, study_name)
    if not os.path.isdir(study_path):
        return None
    return study_path

def get_subject_file_path(subject_name, file_name):
    subject_path = get_subject_path(subject_name)
    file_path = os.path.join(subject_path, file_name)
    return file_path    

def get_study_file_path(subject_name, study_name, file_name):
    study_path = get_study_path(subject_name, study_name)
    file_path = os.path.join(study_path, file_name)
    return file_path

def get_study_files(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not study_path:
        return []
    files = []
    for file_name in sorted(os.listdir(study_path)):
        full_path = os.path.join(study_path, file_name)
        if file_name.startswith('.'):
            continue  # Skip files starting with a period
        if os.path.isfile(full_path):
            files.append({'name': file_name, 'full_path': full_path})
    return files
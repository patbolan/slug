from flask import Blueprint, render_template, abort, request
from utils import (
    get_all_subjects,
    get_studies_for_subject,
    get_study_path,
    get_subject_path,
    get_subject_file_path,
    get_study_file_path,
    get_subject_reports_path,
    get_sample_dicom_header,
    get_file_tree,
    get_series_number_from_folder,
    get_project_reports_path,
    get_server_environment,
    get_subject_type,
    get_study_type
)

from tools.utils import get_tool_menu
import os
import csv

# Create a Blueprint
main_bp = Blueprint('main_bp', __name__)


# Home route
@main_bp.route('/')
def index():
    project_reports_path = get_project_reports_path()
    file_tree = get_file_tree(project_reports_path)
    print(file_tree)
    
    tool_menu = get_tool_menu(subject_name=None, study_name=None)
    server_env = get_server_environment()

    return render_template('index.html', tool_menu=tool_menu, file_tree=file_tree, server_env=server_env)

# List all subjects
@main_bp.route('/subjects')
def subjects():
    subjects = get_all_subjects()
    subjects_with_counts = [
        {
            'subject_name': subject,
            'subject_type': get_subject_type(subject),
            'study_count': len(get_studies_for_subject(subject)),
        }
        for subject in subjects
    ]
    return render_template('subjects.html', subjects=subjects_with_counts)

# All studies
@main_bp.route('/studies')
def studies():
    all_studies = []
    subjects = get_all_subjects()
    for subject in subjects:
        subject_studies = get_studies_for_subject(subject)
        for study in subject_studies:
            study_type = get_study_type(subject, study)
            all_studies.append({'subject': subject, 'study': study, "study_type": study_type})
    all_studies.sort(key=lambda x: x['study'], reverse=True)
    return render_template('studies.html', studies=all_studies)

# Details for one subject
@main_bp.route('/subjects/<subject_name>/studies')
@main_bp.route('/subjects/<subject_name>')
def subject(subject_name):
    notes_file_path = get_subject_file_path(subject_name, 'notes.txt')
    notes = open(notes_file_path, 'r').read() if os.path.isfile(notes_file_path) else ""
    subject_type = get_subject_type(subject_name)
    studies = get_studies_for_subject(subject_name)
    all_studies = []
    for study in studies:
        study_type = get_study_type(subject_name, study)
        all_studies.append({'name':study, "study_type": study_type})

    subject_reports_path = get_subject_reports_path(subject_name)
    file_tree = get_file_tree(subject_reports_path)
    # remove the studies: entries in file_tree that start with "MR-"
    #file_tree = [entry for entry in file_tree if not entry['text'].startswith('MR-')]

    tool_menu = get_tool_menu(subject_name, study_name=None)
    return render_template('subject.html', subject=subject_name, subject_type = subject_type, studies=all_studies, notes=notes, tool_menu=tool_menu, file_tree=file_tree)

# Details for one study
@main_bp.route('/subjects/<subject_name>/studies/<study_name>')
def study(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not os.path.isdir(study_path):
        abort(404)

    notes_file = get_study_file_path(subject_name, study_name, 'notes.txt')
    notes = open(notes_file, 'r').read() if os.path.isfile(notes_file) else ""
    file_tree = get_file_tree(study_path)
    tool_menu = get_tool_menu(subject_name, study_name)

    dicom_path = os.path.join(study_path, 'dicom-original')
    dicom_folders = []
    dicom_tags_path = os.path.join(study_path, 'dicom_tags.csv')
    dicom_tags = {}
    if os.path.isfile(dicom_tags_path):
        with open(dicom_tags_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                if len(row) >= 2:
                    dicom_tags[int(row[0])] = row[1]

    dicom_info = get_sample_dicom_header(subject_name, study_name)
    if os.path.isdir(dicom_path):
        for folder_name in sorted(os.listdir(dicom_path)):
            folder_path = os.path.join(dicom_path, folder_name)
            if os.path.isdir(folder_path):
                series_number = get_series_number_from_folder(folder_name)
                if series_number is not None:
                    tag = dicom_tags.get(series_number, "")
                    dicom_folders.append({
                        'name': folder_name,
                        'relative_path': os.path.join('dicom-original', folder_name),
                        'series_number': series_number,
                        'tag': tag
                    })

    return render_template('study.html', subject=subject_name, study=study_name, notes=notes, tool_menu=tool_menu, file_tree=file_tree, dicom_folders=dicom_folders, dicom_info=dicom_info)
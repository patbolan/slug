from flask import Blueprint, render_template, abort, request
from utils import (
    get_all_subjects,
    get_studies_for_subject,
    get_study_path,
    get_subject_file_path,
    get_study_file_path,
    get_study_files,
    get_sample_dicom_header,
    get_file_tree,
    get_series_number_from_folder,
    get_data_folder,
    get_server_environment,
    is_subject_human,
)

from tools.utils import get_tools_for_project, get_tools_for_subject, get_tools_for_study
import os
import csv

# Create a Blueprint
main_bp = Blueprint('main_bp', __name__)

# Home route
@main_bp.route('/')
def index():
    project_reports_path = os.path.join(get_data_folder(), 'Project_Reports')
    file_tree = get_file_tree(project_reports_path) if os.path.isdir(project_reports_path) else []
    toolset = get_tools_for_project()
    server_env = get_server_environment()

    return render_template('index.html', toolset=toolset, file_tree=file_tree, server_env=server_env)

# List all subjects
@main_bp.route('/subjects')
def subjects():
    subjects = get_all_subjects()
    subjects_with_counts = [
        {
            'subject_name': subject,
            'is_human': is_subject_human(subject),
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
            all_studies.append({'subject': subject, 'study': study})
    all_studies.sort(key=lambda x: x['study'], reverse=True)
    return render_template('studies.html', studies=all_studies)

# Details for one subject
@main_bp.route('/subjects/<subject_name>/studies')
@main_bp.route('/subjects/<subject_name>')
def subject(subject_name):
    notes_file_path = get_subject_file_path(subject_name, 'notes.txt')
    notes = open(notes_file_path, 'r').read() if os.path.isfile(notes_file_path) else ""
    studies = get_studies_for_subject(subject_name)
    subject_reports_path = get_subject_file_path(subject_name, 'Subject_Reports')
    file_tree = get_file_tree(subject_reports_path) if os.path.isdir(subject_reports_path) else []
    toolset = get_tools_for_subject(subject_name)
    return render_template('subject.html', subject=subject_name, studies=studies, notes=notes, toolset=toolset, file_tree=file_tree)

# Details for one study
@main_bp.route('/subjects/<subject_name>/studies/<study_name>')
def study(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not os.path.isdir(study_path):
        abort(404)

    notes_file = get_study_file_path(subject_name, study_name, 'notes.txt')
    notes = open(notes_file, 'r').read() if os.path.isfile(notes_file) else ""
    files = get_study_files(subject_name, study_name)
    file_tree = get_file_tree(study_path)
    toolset = get_tools_for_study(subject_name, study_name)

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

    return render_template('study.html', subject=subject_name, study=study_name, notes=notes, toolset=toolset, files=files, file_tree=file_tree, dicom_folders=dicom_folders, dicom_info=dicom_info)
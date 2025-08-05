from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from utils import (  # Import the utility functions
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
    is_subject_human
)

from tools.utils import get_tools_for_project, get_tools_for_subject, get_tools_for_study

import os
import csv  # Add this import for handling CSV files
import json  # Add this import for handling JSON files
import re  # Add this import for regular expressions

# For DICOM handling
import pydicom
import numpy as np
from matplotlib import pyplot as plt
from io import BytesIO
import base64
import shutil  # Add this import for removing directories
import pwd
import getpass  # For getting the current username

from tools.routes import tools_bp   
from handlers.routes import handlers_bp  # Import the handlers blueprint    

app = Flask(__name__)

# Blueprints (routes in )
app.register_blueprint(tools_bp)   
app.register_blueprint(handlers_bp)  # Assuming handlers_bp is defined in handlers/__init__.py 

# Middleware (?) to handle method overrides 
@app.before_request
def handle_method_override():
    if request.method == 'POST' and '_method' in request.form:
        method = request.form['_method'].upper()
        print(f"Overriding method to: {method}")  # Debugging statement
        if method in ['PUT', 'DELETE']:
            request.environ['REQUEST_METHOD'] = method


# Routes
# Home 
@app.route('/')
def index():

    # Generate file tree for the Project_reports
    project_reports_path = os.path.join(get_data_folder(), 'Project_Reports')
    if os.path.isdir(project_reports_path):
        file_tree = get_file_tree(project_reports_path)
    else:
        file_tree = []

    # Get toolset 
    toolset = get_tools_for_project()

    # Get running environment data
    server_env = get_server_environment()

    return render_template('index.html', 
                           toolset=toolset,
                           file_tree=file_tree, 
                           server_env=server_env)

# List all subjects
@app.route('/subjects')
def subjects():
    subjects = get_all_subjects()
    subjects_with_counts = []

    for subject in subjects:
        studies = get_studies_for_subject(subject)
        subjects_with_counts.append({
            'subject_name': subject,
            'is_human': is_subject_human(subject),
            'study_count': len(studies)
        })

    return render_template('subjects.html', subjects=subjects_with_counts)

# All studies
@app.route('/studies')
def studies():
    all_studies = []
    subjects = get_all_subjects()

    for subject in subjects:
        subject_studies = get_studies_for_subject(subject)
        for study in subject_studies:
            all_studies.append({'subject': subject, 'study': study})

    # Sort all_studies by study name, in reverse order
    all_studies.sort(key=lambda x: x['study'], reverse=True)

    return render_template('studies.html', studies=all_studies)

# Details for one subject. By default this will include a list of all studies
@app.route('/subjects/<subject_name>/studies')
@app.route('/subjects/<subject_name>')
def subject(subject_name):
    # Read notes.txt if it exists
    notes_file_path = get_subject_file_path(subject_name, 'notes.txt')
    if os.path.isfile(notes_file_path):
        with open(notes_file_path, 'r') as f:
            notes = f.read()
    else:
        notes = ""

    studies = get_studies_for_subject(subject_name)

    # Generate file tree for the subject
    # Note: the folder name "Subject_Reports" is hardwired here and in "subject.html"
    subject_reports_path = get_subject_file_path(subject_name, 'Subject_Reports')
    if os.path.isdir(subject_reports_path):
        file_tree = get_file_tree(subject_reports_path)
    else:
        file_tree = []

    # Get toolset 
    toolset = get_tools_for_subject(subject_name) 

    return render_template('subject.html', 
                           subject=subject_name, 
                           studies=studies, 
                           notes=notes, 
                           toolset=toolset,
                           file_tree=file_tree)



# One study. 
@app.route('/subjects/<subject_name>/studies/<study_name>')
def study(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not os.path.isdir(study_path):
        abort(404)

    # Read notes.txt if it exists
    notes_file = get_study_file_path(subject_name, study_name, 'notes.txt')
    if os.path.isfile(notes_file):
        with open(notes_file, 'r') as f:
            notes = f.read()
    else:
        notes = ""

    files = get_study_files(subject_name, study_name)

    # Generate file tree
    file_tree = get_file_tree(study_path)

    # Get toolset 
    toolset = get_tools_for_study(subject_name, study_name) 


    # Process DICOM folders
    dicom_path = os.path.join(study_path, 'dicom-original')
    dicom_folders = []
    dicom_tags_path = os.path.join(study_path, 'dicom_tags.csv')

    # Read tags from dicom_tags.csv
    dicom_tags = {}
    if os.path.isfile(dicom_tags_path):
        with open(dicom_tags_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader) # Skip header row
            for row in reader:
                if len(row) >= 2:
                    dicom_tags[int(row[0])] = row[1]

    # Read sample dicom metadata
    dicom_info = get_sample_dicom_header(subject_name, study_name)
    if dicom_info == None:
        print('Unable to find dicom info')

    # Process folders under dicom-original
    if os.path.isdir(dicom_path):
        for folder_name in sorted(os.listdir(dicom_path)):
            folder_path = os.path.join(dicom_path, folder_name)
            if os.path.isdir(folder_path):
                # Use the new utility function to extract the series number
                series_number = get_series_number_from_folder(folder_name)
                if series_number is not None:
                    tag = dicom_tags.get(series_number, "")
                    dicom_folders.append({
                        'name': folder_name,
                        'relative_path': os.path.join('dicom-original', folder_name),
                        'series_number': series_number,
                        'tag': tag
                    })

    return render_template('study.html', 
                           subject=subject_name, 
                           study=study_name, 
                           notes=notes, 
                           toolset=toolset,
                           files=files, 
                           file_tree=file_tree, 
                           dicom_folders=dicom_folders, 
                           dicom_info=dicom_info)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Run on all interfaces at port 5000

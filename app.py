from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from utils import (  # Import the utility functions
    get_all_subjects,
    get_studies_for_subject,
    get_subject_path,
    get_study_path,
    get_subject_file_path,
    get_study_file_path,
    get_study_files, 
    get_sample_dicom_header, 
    get_file_tree,
    get_series_number_from_folder
)
from tools import *
from process_manager import ProcessManager

import os
from datetime import datetime
import random
import time
import csv  # Add this import for handling CSV files
import json  # Add this import for handling JSON files
import re  # Add this import for regular expressions

# For DICOM handling
import pydicom
import numpy as np
from matplotlib import pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)




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
    return render_template('index.html')

# List all subjects
@app.route('/subjects')
def subjects():
    subjects = get_all_subjects()
    subjects_with_counts = []

    for subject in subjects:
        studies = get_studies_for_subject(subject)
        subjects_with_counts.append((subject, len(studies)))

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

    return render_template('subject.html', 
                           subject=subject_name, 
                           studies=studies, 
                           notes=notes, 
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
                    # tag = dicom_tags.get(series_number, "No Tag")
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
                           dicom_info = dicom_info)


# But using the "path:" keyword, all the path information after will get assigned to one variable
@app.route('/viewer/subjects/<subject_name>/studies/<study_name>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
@app.route('/viewer/subjects/<subject_name>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
@app.route('/viewer/process/<process_id>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
def file_viewer(file_relative_path, subject_name=None, study_name=None, process_id=None):
    print(f'file_viewer: subject_name={subject_name}, file_relative_path={file_relative_path}, study_name={study_name}, process_id={process_id}')
    # Construct the full file path based on whether study_name is provided
    if study_name is not None:
        # Study-associated file
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    elif subject_name is not None:
        # Subject-associated file
        file_path = get_subject_file_path(subject_name, file_relative_path)
    elif process_id is not None:
        file_path = get_processs_file_path(process_id)
    else:
        # Todo: project-associated files? Reports?
        print('file_viewer: unsupported file association')
        abort(404)

    # HACK - the javascript sometimes adds an extra path delimiter. 
    file_path = re.sub(r'/+', '/', file_path)
    print(f'file_viewer: file_path = {file_path}')

    # Get File type
    _, ext = os.path.splitext(file_path)
    ext = ext[1:]  # Get rid of the period

    if ext in ('txt', 'csv', 'json'):
        # Existing logic for text files
        if request.method == 'PUT':
            # Create a blank file if it does not exist
            if not os.path.isfile(file_path):
                with open(file_path, 'w') as f:
                    f.write("")  # Write an empty string to create the file
                print(f"Created blank file: {file_path}")
                return f"Created blank file: {file_relative_path}", 201
            else:
                print(f"File already exists: {file_path}")
                return f"File already exists: {file_relative_path}", 409

        # Check if the file exists for GET requests
        if not os.path.isfile(file_path):
            print('file_viewer: Invalid file path:', file_path)
            abort(404)

        if ext == 'txt':
            # Read the content of the text file
            with open(file_path, 'r') as f:
                content = f.read()

        elif ext == 'csv':
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                content = '\n'.join([','.join(row) for row in reader])

        elif ext == 'json':
            with open(file_path, encoding='utf-8') as jsonfile:
                content = json.dumps(json.load(jsonfile), indent=4)

        else:
            content = "Unsupported file type."

        return render_template('text.html', 
                            subject=subject_name, 
                            study=study_name, 
                            filepath=file_relative_path, 
                            content=content)
    
    elif ext in ('nii'):
        # Note that I accidently deleted this logic when I "REmoved Collections"
        print('Rendering NIFTI:', file_path)
        if not os.path.isfile(file_path):
            abort(404)

        return render_template('nifti.html', 
                            subject=subject_name, 
                            study=study_name, 
                            file_path=file_path, )
    elif ext in ('png'):
        # Handle PNG files
        if not os.path.isfile(file_path):
            print('file_viewer: Invalid file path:', file_path)
            abort(404)
        return send_file(file_path, mimetype='image/png')
        

    elif ext == 'dcm':
        # Handle DICOM files
        if not os.path.isfile(file_path):
            print('file_viewer: Invalid file path:', file_path)
            abort(404)

        # Read the DICOM file
        dicom_data = pydicom.dcmread(file_path)

        # Extract header information
        header_info = dicom_data

        # Extract image data
        if hasattr(dicom_data, 'pixel_array'):
            image_data = dicom_data.pixel_array

            # Render the image using matplotlib
            plt.imshow(image_data, cmap='gray')
            plt.axis('off')
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()
        else:
            image_base64 = None

        return render_template('dicom.html',
                               subject=subject_name,
                               study=study_name,
                               filepath=file_relative_path,
                               header_info=header_info,
                               image_base64=image_base64)
    else:
        print('file_viewer: Invalid file type:', file_path)
        abort(404) 


@app.route('/nifti-files/<path:filename>')
def serve_nifti(filename):
    # For reasons I don't understand, the leading slash is stripped from the filename. Add it back
    file_path = '/' + filename
    print('Serving NIFTI file:', file_path)
    if not os.path.isfile(file_path):
        abort(404)
    return send_file(file_path)


@app.route('/dicom-file/<path:filename>')  
def serve_dicom_file(filename):  
    # For reasons I don't understand, the leading slash is stripped from the filename. Add it back
    filename = '/' + filename
    #print('Serving DICOM file:', filename) # Called many times
    if not os.path.isfile(filename):
        abort(404)
    return send_file(filename, mimetype='application/dicom')

@app.route('/dicom-series/subjects/<subject_name>/studies/<study_name>/<path:series_relative_path>', methods=['GET'])
def dicom_series_viewer(subject_name, study_name, series_relative_path):
    print(f'dicom_series_viewer: subject_name={subject_name}, study_name={study_name}, \
          series_relative_path={series_relative_path}')

    # Construct the full path to the DICOM series
    series_path = get_study_file_path(subject_name, study_name, series_relative_path)

    # Check if the series path exists
    if not os.path.isdir(series_path):
        print('dicom_series_viewer: Invalid series path:', series_path)
        abort(404)

    # Get all DICOM files in the series
    dicom_files = [os.path.join(series_path, f) for f in os.listdir(series_path) if f.endswith('.dcm')]
    dicom_files.sort() # TODO: needs special sorting

    dicom_urls = [url_for('serve_dicom_file', filename=f ) for f in dicom_files] 

    # print('Here are the URLs:')
    # for url in dicom_urls:
    #     print(url)

    return render_template('dicom_series.html', dicom_urls=dicom_urls)



@app.route('/edit/subjects/<subject_name>/studies/<study_name>/<path:file_relative_path>', methods=['POST'])
@app.route('/edit/subjects/<subject_name>/<path:file_relative_path>', methods=['POST'])
def edit_file(subject_name, study_name=None, file_relative_path=None):

    # Construct the full file path based on whether study_name is provided
    if study_name:
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    else:
        file_path = get_subject_file_path(subject_name, file_relative_path)
    
    # Check if the file exists
    if not os.path.isfile(file_path):
        print('edit_file: Invalid file path:', file_path)
        abort(404)

    # Get the updated content from the form
    updated_content = request.form.get('content', '')

    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)

    # Redirect back to the viewer route
    return redirect(url_for('file_viewer', subject_name=subject_name, study_name=study_name, file_relative_path=file_relative_path))

@app.route('/edit-page/subjects/<subject_name>/studies/<study_name>/<path:file_relative_path>', methods=['GET'])
@app.route('/edit-page/subjects/<subject_name>/<path:file_relative_path>', methods=['GET'])
def edit_file_page(subject_name, study_name=None, file_relative_path=None):
    # Construct the full file path based on whether study_name is provided
    if study_name:
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    else:
        file_path = get_subject_file_path(subject_name, file_relative_path)

    # Check if the file exists
    if not os.path.isfile(file_path):
        print('edit_file_page: Invalid file path:', file_path)
        abort(404)

    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()

    return render_template('edit_file.html', 
                           subject=subject_name, 
                           study=study_name, 
                           filepath=file_relative_path, 
                           content=content)

@app.route('/tools/<tool_name>/<command>/subjects/<subject_name>/studies/<study_name>/', methods=['POST'])
def tool_command(tool_name, command, subject_name, study_name):

    print(f"Tool: {tool_name}, Command: {command}, Subject: {subject_name}, Study: {study_name}")
    execute_tool(tool_name, command, subject_name, study_name)
    return f"Tool '{tool_name}' executed command '{command}' for subject '{subject_name}' and study '{study_name}'.", 200

@app.route('/processes')
def processes():
    # Create an instance of ProcessManager
    process_manager = ProcessManager()

    # Get the list of running and completed processes
    running_processes = process_manager.get_processes(folder_type='running')
    completed_processes = process_manager.get_processes(folder_type='completed')

    # Render the processes.html template with both lists
    return render_template('processes.html', 
                           running_processes=running_processes, 
                           completed_processes=completed_processes)

@app.route('/process/<pid>')
def process_info(pid):
    # Create an instance of ProcessManager
    process_manager = ProcessManager()

    # Get process information
    process_info = process_manager.get_process_info(pid)

    # If the process does not exist, return a 404 error
    if not process_info:
        abort(404, description=f"Process with PID {pid} not found.")

    return render_template('process.html', process_info=process_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Run on all interfaces at port 5000

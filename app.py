from flask import Flask, render_template, abort, request, redirect, url_for, send_file
import os
from datetime import datetime
import random
import time
import csv  # Add this import for handling CSV files
import json  # Add this import for handling JSON files
import re  # Add this import for regular expressions

app = Flask(__name__)
DATA_DIR = '/home/bakken-raid8/pcad2/data'


def get_all_subjects():
    pattern = re.compile(r'^[A-Z]{3}-\d{4}$')  # Pattern for XXX-0000
    subjects = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d)) and pattern.match(d)]
    subjects.sort()
    return subjects

def get_studies_for_subject(subject_name):
    subject_path = os.path.join(DATA_DIR, subject_name)
    if not os.path.isdir(subject_path):
        return []
    pattern = re.compile(r'MR-\d{8}$')  # Pattern for MR-YYYYMMDD
    studies = [d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d)) and pattern.match(d)]
    studies.sort()
    return studies



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

# Details for one subject. By default this will include a list of all studies
@app.route('/subjects/<subject_name>/studies')
@app.route('/subjects/<subject_name>')
def subject(subject_name):
    studies = get_studies_for_subject(subject_name)
    return render_template('subject.html', subject=subject_name, studies=studies)

# One study. Also list collections
@app.route('/subjects/<subject_name>/studies/<study_name>/collections')
@app.route('/subjects/<subject_name>/studies/<study_name>')
def study(subject_name, study_name):
    study_path = os.path.join(DATA_DIR, subject_name, study_name)
    if not os.path.isdir(study_path):
        abort(404)

    files = []
    collections = []
    for file_name in sorted(os.listdir(study_path)):
        full_path = os.path.join(study_path, file_name)
        if file_name.startswith('.'):
            continue  # Skip files starting with a period
        if os.path.isfile(full_path):
            timestamp = datetime.fromtimestamp(os.path.getmtime(full_path))
            files.append({'name': file_name, 'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')})
        else: # Folders are considered collections
            collections.append({'name': file_name})

    return render_template('study.html', 
                           subject=subject_name, study=study_name, files=files, collections=collections)


@app.route('/subject/<subject_name>/studies/<study_name>/collections/<collection_name>')
def collection(subject_name, study_name, collection_name):
    collection_path = os.path.join(DATA_DIR, subject_name, study_name, collection_name)
    if not os.path.isdir(collection_path):
        abort(404)

    files = []
    folders = []
    for file_name in sorted(os.listdir(collection_path)):
        full_path = os.path.join(collection_path, file_name)
        if file_name.startswith('.'):
            continue  # Skip files starting with a period
        if os.path.isfile(full_path):
            timestamp = datetime.fromtimestamp(os.path.getmtime(full_path))
            files.append({'name': file_name, 'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            folders.append({'name': file_name})

    return render_template('collection.html', 
                           subject=subject_name, 
                           study=study_name, 
                           collection_name=collection_name, 
                           files=files, folders=folders)

#@app.route('/subject/<subject_name>/<study_name>/<file_name>')
@app.route('/subject/<subject_name>/studies/<study_name>/<file_name>')
#@app.route('/subject/<subject_name>/studies/<study_name>/collections/<collection_name>/files/<file_name>')
def render_csv(subject_name, study_name, file_name):
    file_path = os.path.join(DATA_DIR, subject_name, study_name, file_name)
    if not os.path.isfile(file_path) or not file_name.endswith('.csv'):
        print('Invalid file path or not a CSV file:', file_path)
        abort(404)

    csv_data = []
    with open(file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        csv_data = list(reader)

    return render_template('csv.html', 
                           subject=subject_name, 
                           study=study_name,  
                           file_name=file_name, 
                           csv_data=csv_data)

@app.route('/json/<subject_name>/studies/<study_name>/collections/<collection_name>/files/<file_name>')
def render_json(subject_name, study_name, collection_name, file_name):
    file_path = os.path.join(DATA_DIR, subject_name, study_name, collection_name, file_name)
    if not os.path.isfile(file_path) or not file_name.endswith('.json'):
        abort(404)

    with open(file_path, 'r') as json_file:
        json_data = json.load(json_file)

    # Format JSON data with indentation for readability
    formatted_json = json.dumps(json_data, indent=4)

    return render_template('json.html', 
                           subject=subject_name, 
                           study=study_name, 
                           collection_name=collection_name, 
                           file_name=file_name, 
                           json_data=formatted_json)

@app.route('/nifti/<subject_name>/studies/<study_name>/collections/<collection_name>/files/<file_name>')
def render_nifti(subject_name, study_name, collection_name, file_name):
    print('Rendering NIFTI:', subject_name, study_name, collection_name, file_name)
    file_path = os.path.join(DATA_DIR, subject_name, study_name, collection_name, file_name)
    print('Rendering NIFTI:', file_path)
    if not os.path.isfile(file_path) or not file_name.endswith('.nii'):
        abort(404)

    return render_template('nifti.html', 
                           subject=subject_name, 
                           study=study_name, 
                           collection_name=collection_name, 
                           file_path=file_path, )

@app.route('/nifti-files/<path:filename>')
def serve_nifti(filename):
    # For reasons I don't understand, the leading slash is stripped from the filename. Add it back
    file_path = '/' + filename
    print('Serving NIFTI file:', file_path)
    if not os.path.isfile(file_path):
        abort(404)
    return send_file(file_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Run on all interfaces at port 5000

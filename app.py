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

## Utility functions to access subjects and studies
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

def get_collections_for_study(subject_name, study_name):
    study_path = get_study_path(subject_name, study_name)
    if not study_path:
        return []
    collections = [d for d in os.listdir(study_path) if os.path.isdir(os.path.join(study_path, d)) and not d.startswith('.')]
    collections.sort()
    return collections

# Keep all the path building functions together
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

def get_collection_path(subject_name, study_name, collection_name):
    study_path = get_study_path(subject_name, study_name)
    if not study_path:
        return None
    collection_path = os.path.join(study_path, collection_name)
    if not os.path.isdir(collection_path):
        return None
    return collection_path

# If you request a file, you get the full path. Does not test if the file exists.
def get_subject_file_path(subject_name, file_name):
    subject_path = get_subject_path(subject_name)
    file_path = os.path.join(subject_path, file_name)
    return file_path    

def get_study_file_path(subject_name, study_name, file_name):
    study_path = get_study_path(subject_name, study_name)
    file_path = os.path.join(study_path, file_name)
    return file_path

def get_collection_file_path(subject_name, study_name, collection_name, file_name):
    collection_path = get_collection_path(subject_name, study_name, collection_name)
    file_path = os.path.join(collection_path, file_name)
    return file_path

# These a list of files in a study, with their full paths and timestamps
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
    return render_template('subject.html', subject=subject_name, studies=studies, notes=notes)

def get_file_tree(path):
    """
    Recursively generates a hierarchical file tree for the given path.
    :param path: Root directory path.
    :return: List representing the file tree.
    """
    tree = []
    for entry in sorted(os.listdir(path)):
        if entry.startswith('.'):  # Ignore files or folders starting with a period
            continue
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            tree.append({
                'text': entry,
                'icon': 'jstree-folder',  # Folder icon
                'children': get_file_tree(full_path),
                'full_path': full_path
            })
        else:
            tree.append({
                'text': entry,
                'icon': 'jstree-file',  # File icon
                'full_path': full_path
            })
    return tree

# One study. Also list collections
@app.route('/subjects/<subject_name>/studies/<study_name>/collections')
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
    collections = get_collections_for_study(subject_name, study_name)

    # Generate file tree
    file_tree = get_file_tree(study_path)

    return render_template('study.html', 
                           subject=subject_name, 
                           study=study_name, 
                           notes=notes, 
                           files=files, 
                           collections=collections, 
                           file_tree=file_tree)


@app.route('/subject/<subject_name>/studies/<study_name>/collections/<collection_name>')
def collection(subject_name, study_name, collection_name):
    collection_path = get_collection_path(subject_name, study_name, collection_name)
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
            files.append({'name': file_name, 'full_path': full_path})
        else:
            folders.append({'name': file_name, 'full_path': full_path})

    return render_template('collection.html', 
                           subject=subject_name, 
                           study=study_name, 
                           collection_name=collection_name, 
                           files=files, folders=folders)

# But using the "path:" keyword, all the path information after will get assigned to one variable
@app.route('/viewer/subjects/<subject_name>/studies/<study_name>/<path:file_relative_path>')
def file_viewer(subject_name, study_name, file_relative_path):

    # Construct the full file path
    file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    
    # Check if the file exists and is a text file
    if not os.path.isfile(file_path):
        print('text_viewer: Invalid file path:', file_path)
        abort(404)
    
    if file_relative_path.endswith('.txt'):
        # Read the content of the text file
        with open(file_path, 'r') as f:
            content = f.read()

    elif file_relative_path.endswith('csv'):
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # TODO needs line breaks
            reader = csv.reader(csvfile)
            #content = list(reader)
            content = '\n'.join([','.join(row) for row in reader])

    elif file_relative_path.endswith('json'):
        with open(file_path, encoding='utf-8') as jsonfile:
            #content = json.load(jsonfile)
            content = json.dumps(json.load(jsonfile), indent=4)

    else:
        content

    return render_template('text.html', 
                           subject=subject_name, 
                           study=study_name, 
                           filepath=file_relative_path, 
                           content=content)


#@app.route('/subject/<subject_name>/<study_name>/<file_name>')
@app.route('/subject/<subject_name>/studies/<study_name>/<file_name>')
@app.route('/subjects/<subject_name>/studies/<study_name>/<file_name>')
#@app.route('/subject/<subject_name>/studies/<study_name>/collections/<collection_name>/files/<file_name>')
def render_csv(subject_name, study_name, file_name):
    file_path = get_study_file_path(subject_name, study_name, file_name)
    if not os.path.isfile(file_path) or not file_name.endswith('.csv'):
        print('render_csv: Invalid file path or not a CSV file:', file_path)
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
    collection_path = get_collection_path(subject_name, study_name, collection_name)
    file_path = os.path.join(collection_path, file_name)
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
    collection_path = get_collection_path(subject_name, study_name, collection_name)
    file_path = os.path.join(collection_path, file_name)
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


@app.route('/notes/<subject_name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def subject_note(subject_name):   

    notes_file_path = get_subject_file_path(subject_name, 'notes.txt')

    if request.method == 'GET':
        # Read notes.txt if it exists
        if os.path.isfile(notes_file_path):
            with open(notes_file_path, 'r') as f:
                notes = f.read()
        else:
            notes = "<enter notes here>"
        print("Calling render with notes:", notes)  # Debugging statement
        return render_template('notes.html', subject_name=subject_name, notes=notes)

    elif request.method == 'POST':
        # Update notes.txt with the submitted content
        new_notes = request.form.get('notes', '')
        with open(notes_file_path, 'w') as f:
            f.write(new_notes)
        return redirect(url_for('subject_note', subject_name=subject_name))

    elif request.method == 'PUT':
        # Create notes.txt if it doesn't exist
        if not os.path.isfile(notes_file_path):
            with open(notes_file_path, 'w') as f:
                f.write("")
            return redirect(url_for('subject_note', subject_name=subject_name))
        else:
            return f"notes.txt already exists for subject {subject_name}", 409

    elif request.method == 'DELETE':
        print(f"DELETE notes.txt request received for subject: {subject_name}")  # Debugging statement
        if os.path.isfile(notes_file_path):
            print('Deleting notes file:', notes_file_path)  # Debugging statement
            os.remove(notes_file_path)
            return f"Deleted notes.txt for subject {subject_name}", 200
        else:
            print('notes.txt does not exist')  # Debugging statement
            return f"notes.txt does not exist for subject {subject_name}", 404

@app.route('/notes/<subject_name>/studies/<study_name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def study_note(subject_name, study_name):

    notes_file_path = get_study_file_path(subject_name, study_name, 'notes.txt')

    if request.method == 'GET':
        # Read notes.txt if it exists
        if os.path.isfile(notes_file_path):
            with open(notes_file_path, 'r') as f:
                notes = f.read()
        else:
            notes = "<enter notes here>"
        
        print("Calling render with notes:", notes)  # Debugging statement
        return render_template('notes.html', subject_name=subject_name, study_name=study_name, notes=notes)

    elif request.method == 'POST':
        # Update notes.txt with the submitted content
        new_notes = request.form.get('notes', '')
        with open(notes_file_path, 'w') as f:
            f.write(new_notes)
        return redirect(url_for('study_note', subject_name=subject_name, study_name=study_name))

    elif request.method == 'PUT':
        # Create notes.txt if it doesn't exist
        if not os.path.isfile(notes_file_path):
            with open(notes_file_path, 'w') as f:
                f.write("")
            return redirect(url_for('study_note', subject_name=subject_name, study_name=study_name))
        else:
            return f"notes.txt already exists for study {study_name}", 409

    elif request.method == 'DELETE':
        print(f"DELETE request received for study: {study_name}")  # Debugging statement
        if os.path.isfile(notes_file_path):
            print('Deleting notes file:', notes_file_path)  # Debugging statement
            os.remove(notes_file_path)
            return f"Deleted notes.txt for study {study_name}", 200
        else:
            print('notes.txt does not exist')  # Debugging statement
            return f"notes.txt does not exist for study {study_name}", 404





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Run on all interfaces at port 5000

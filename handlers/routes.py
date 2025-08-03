from flask import Blueprint, render_template, abort, redirect, url_for, send_file, request

from utils import get_process_file_path, get_file_tree, get_study_file_path, get_subject_file_path, get_data_folder
import os
import csv
import json
import re
import pydicom
import matplotlib.pyplot as plt
from io import BytesIO
import base64


handlers_bp = Blueprint('handlers_bp', __name__)


# But using the "path:" keyword, all the path information after will get assigned to one variable
@handlers_bp.route('/viewer/subjects/<subject_name>/studies/<study_name>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
@handlers_bp.route('/viewer/subjects/<subject_name>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
@handlers_bp.route('/viewer/files/<path:file_relative_path>', methods=['GET', 'PUT'])
@handlers_bp.route('/viewer/process/<process_id>/files/<path:file_relative_path>', methods=['GET', 'PUT'])
def file_viewer(file_relative_path, subject_name=None, study_name=None, process_id=None):
    print(f'file_viewer: subject_name={subject_name}, file_relative_path={file_relative_path}, study_name={study_name}, process_id={process_id}')
    # Construct the full file path based on whether study_name is provided
    if study_name is not None:
        # Study-associated file
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
        readonly = False
    elif subject_name is not None:
        # Subject-associated file
        file_path = get_subject_file_path(subject_name, file_relative_path)
        readonly = False
    elif process_id is not None:
        file_path = get_process_file_path(process_id, file_relative_path)
        readonly = True
    else:
        file_path = os.path.join(get_data_folder(), file_relative_path)
        readonly = False

    # HACK - the javascript sometimes adds an extra path delimiter. 
    file_path = re.sub(r'/+', '/', file_path)
    print(f'file_viewer: file_path = {file_path}')

    # Get File type
    _, ext = os.path.splitext(file_path)
    ext = ext[1:].lower()  # Get rid of the period

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
                            content=content, 
                            readonly=readonly, 
                            process_id = process_id)
    
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


@handlers_bp.route('/nifti-files/<path:filename>')
def serve_nifti(filename):
    # For reasons I don't understand, the leading slash is stripped from the filename. Add it back
    file_path = '/' + filename
    print('Serving NIFTI file:', file_path)
    if not os.path.isfile(file_path):
        abort(404)
    return send_file(file_path)


@handlers_bp.route('/dicom-file/<path:filename>')  
def serve_dicom_file(filename):  
    # For reasons I don't understand, the leading slash is stripped from the filename. Add it back
    filename = '/' + filename
    #print('Serving DICOM file:', filename) # Called many times
    if not os.path.isfile(filename):
        abort(404)
    return send_file(filename, mimetype='application/dicom')

@handlers_bp.route('/dicom-series/subjects/<subject_name>/studies/<study_name>/<path:series_relative_path>', methods=['GET'])
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

    dicom_urls = [url_for('handlers_bp.serve_dicom_file', filename=f ) for f in dicom_files] 

    # print('Here are the URLs:')
    # for url in dicom_urls:
    #     print(url)

    return render_template('dicom_series.html', dicom_urls=dicom_urls)


# TODO Not sure this function is used. There's a edit_file_page, and a file_viewer. Clean up
@handlers_bp.route('/edit/subjects/<subject_name>/studies/<study_name>/<path:file_relative_path>', methods=['POST'])
@handlers_bp.route('/edit/subjects/<subject_name>/<path:file_relative_path>', methods=['POST'])
@handlers_bp.route('/edit/<path:file_relative_path>', methods=['POST'])
def edit_file(subject_name=None, study_name=None, file_relative_path=None):
    # Construct the full file path based on whether study_name is provided
    if study_name:
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    elif subject_name:
        file_path = get_subject_file_path(subject_name, file_relative_path)
    else:
        file_path = os.path.join(get_data_folder(), file_relative_path)

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
    return redirect(url_for('handlers_bp.file_viewer', 
                            subject_name=subject_name, 
                            study_name=study_name, 
                            file_relative_path=file_relative_path))

@handlers_bp.route('/edit-page/subjects/<subject_name>/studies/<study_name>/<path:file_relative_path>', methods=['GET'])
@handlers_bp.route('/edit-page/subjects/<subject_name>/<path:file_relative_path>', methods=['GET'])
@handlers_bp.route('/edit-page/<path:file_relative_path>', methods=['GET'])
def edit_file_page(subject_name=None, study_name=None, file_relative_path=None):
    # Construct the full file path based on whether study_name is provided
    if study_name:
        file_path = get_study_file_path(subject_name, study_name, file_relative_path)
    elif subject_name:
        file_path = get_subject_file_path(subject_name, file_relative_path)
    else:
        file_path = os.path.join(get_data_folder(), file_relative_path)

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

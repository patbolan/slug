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
    is_subject_human, 
    get_port_for_user
)

from tools.utils import get_tools_for_project, get_tools_for_subject, get_tools_for_study

import os
import csv  # Add this import for handling CSV files
import json  # Add this import for handling JSON files
import getpass

import numpy as np
from matplotlib import pyplot as plt
from io import BytesIO


from tools.routes import tools_bp   
from handlers.routes import handlers_bp  # Import the handlers blueprint    
from main_routes import main_bp  # Import the main routes blueprint


app = Flask(__name__)

# Blueprints (routes are other files)
app.register_blueprint(main_bp)
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


if __name__ == '__main__':
    """
    For debugging, use 'flask run --host=0.0.0.0'. That doesnt' run this function, 
    but just starts the flask development server on port 5000.

    For local running, use 'python app.py'. That'll execute this code.
    """
    username = getpass.getuser()
    port = get_port_for_user(username)
    print(f'Starting server on port {port} for user {username}')

    app.run(host='0.0.0.0', port=port)  # Run on all interfaces at port 5000

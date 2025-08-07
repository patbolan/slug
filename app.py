from flask import Flask, request
from utils import (  # Import the utility functions
    get_port_for_user, 
    get_web_browser_path
)

import getpass
import argparse

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

def parse_arguments():
    """
    Parses command-line arguments for the application.
    """
    parser = argparse.ArgumentParser(description="Run the Flask application.")
    parser.add_argument(
        "--mode",
        choices=["local", "network"],
        default="local",
        help="Specify the mode: 'local' (default) or 'network'.",
    )

    return parser.parse_args()

if __name__ == '__main__':
    """
    For debugging, use 'flask run --host=0.0.0.0'. That doesnt' run this function, 
    but just starts the flask development server on port 5000.

    For local running, use 'python app.py'. That'll execute this code.
    """
    args = parse_arguments()

    username = getpass.getuser()
    port = get_port_for_user(username)

    if args.mode == "network":
        host = '127.0.0.1'
        print(f'Starting server on host {host}:{port} for user {username}')
        app.run(host=host, port=port)  # Run on all interfaces at port 5000

    else:
        # Local version. Here we'll fire off a server instance as a background thread,
        # then run the pywebview window. 
        print(f'Starting local server on port {port} for user {username}') 

        # Now run app.run() in a background thread
        from threading import Thread
        #server_thread = Thread(target=app.run, kwargs={'port': port})
        # HEre is a hack - I am opening up the server to all interfaces, so that it can be accessed 
        # from other devices on the network. Suitable for debugging. 
        server_thread = Thread(target=app.run, kwargs={'port': port, 'host': '0.0.0.0'})
        server_thread.start()

        if False:
            # Now start a pywebview window
            # Problem with this approach is that it doesn't support tabs, so when you open in a new 
            # tab it opens the default browser instead of the webview.
            import webview
            webview.create_window('My App', 'http://127.0.0.1:' + str(port), width=1000, height=1200)
            webview.start()  # Start the webview event loop
        else:
            # Tried to webbrowser module, but it returns right away, and I want to wait for the proc to finish
            browser_cmd = get_web_browser_path()
            url = 'http://127.0.0.1:' + str(port)
            import subprocess
            process = subprocess.Popen([browser_cmd, url])

            # Wait for the browser process to complete
            process.wait()

        # When the browser is closed, we can stop the server thread
        server_thread.join(timeout=1)  # Wait for the server thread to finish
        print("Server thread has been stopped.")

        # Terminate the process
        import os
        os._exit(0)  # Exit the application cleanly




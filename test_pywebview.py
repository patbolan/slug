# To get this working I installed the following
# pip install pywebview pyqt5 pyqtwebengine pyqt

import webview
#webview.create_window('Hello World', 'https://pywebview.flowrl.com/')
webview.create_window('Slug', 'http://bakken.cmrr.umn.edu:5000')
webview.start()


print('webview has terminated')
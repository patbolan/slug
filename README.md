# SLUG
Slug is a web application used to manage data and processes for imaging research studies. It uses a FLASK 
back end, and a very light front end (just jinja templates) to browse subject/study/series data 
through a web browser. There is no database - the state of the system is defined by the underlying
file structure. 

This program was written by Patrick Bolan. It is an updated implementation of Matlab-based tools 
built over ~15 years for managing a variety of research studies. This initial version of SLUG is 
specifically to support Greg Metzger's quantitative protate studies, funded under 
[R01CA241159-04](https://reporter.nih.gov/search/3TEMqajQiU6ytIJmAYJcLw/project-details/10919247).

Processing tools were written by Leo Bao. Integration of the system and code was performed by Bao, 
Metzger, and Bolan. The name *Slug* is just an arbitrary code word: I use random four-letter animal 
names for programing projects, and this is a little more advanced than the *Worm* project. 

## IMplementation issues
The initial version of this app will not be a proper server. Instead each user logs into server (bakken) and
starts up their own server, then uses the browser on server to interact. Somewaht inconvenient,
but allows tight security (only localhost), simplicity.

To make a proper server we'll need
* https and certificates
* authentication (system-specific users, x.500, token)
* server management (start, stop, update)

Explored flaskwebui and pywebview. Maybe pywebview is appropriate, but recognoize that other users
on the server can access the port.



## Progress Notes
Was starting to implement reports, and I think we should meet and discuss instead of plow ahead. 
First, they way we're going right now the reports (and convert, etc) can be implemented as command-line modules
Maybe we should continue like that? Could help modularize the development. 

If so, need Leo to start moving his code up to server. 


## Next Steps
* move the code to pcad2. 
* Push to github repository


## TODO


## Bugs
* Leo, report_functions line 1993



## Future
* Use a better dicom viewer. Cornerstone.js?
* Make a nice frontend in React
* The file trees are a little awkward. Browse files like github does.
* Add Projects for highest level organization
* Add Users, groups, and permissions.
* Provide a new study or new subject feature. Upload dicoms, parse them out. 

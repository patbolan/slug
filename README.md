# SLUG
Slug is a web application used to manage data and processes for imaging research studies. It uses a FLASK 
back end, and a very light front end (just jinja templates) to browse subject/study/series data 
through a web browser. There is no database - the state of the system is defined by the underlying
file structure. 

This program was written by Patrick Bolan. It is an updated implementation of Matlab-based tools 
built over ~15 years for managing a variety of research studies. This initial version of SLUG is 
specifically to support Greg Metzger's quantitative protate studies, funded under 
[R01CA241159-04](https://reporter.nih.gov/search/3TEMqajQiU6ytIJmAYJcLw/project-details/10919247).

Processing tools were written mostly by Leo Bao. Integration of the system and code was performed by 
Bao, Metzger, and Bolan. The name *Slug* is just an arbitrary code word: I use random four-letter animal 
names for programing projects, and this is a little more advanced than the *Worm* project. 

## Implementation issues
The initial version of this app will not be a proper server. Instead each user logs into server (bakken) and
starts up their own server, then uses the browser on server to interact. Somewaht inconvenient,
but allows tight security (only localhost), simplicity.

To make a proper server we'll need: 
* https and certificates
* authentication (system-specific users, x.500, token)
* server management (start, stop, update)

So, for now I implemented --mode=local and --mode=network. Local starts a background service that 
listens only on localhost, then opens a browser on Bakken with that URL. When the browser is closed 
the service is stopped. This is the secure option

## Next Steps
* pull from github to  pcad2. Test, and notify Leo and Greg
* reports

## Future
* Use a better dicom viewer. Cornerstone.js?
* Make a nice frontend in React
* The file trees are a little awkward. Browse files like github does.
* Add Projects for highest level organization

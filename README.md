# VQL Manager
An Application to manage Denodo scripts
This application supports:
> Splitting up code to create a repository

> Read in such repository and view in a working model

> Compare two models on changed code, additions and deletes

Managing the vql codebase from Denodo is complex.
Denodo objects have relationships with each other.
Removing a parent object could cause the children to be deleted as well.
Currently the integration with Git is not working as expected.

The rationale behind this tool is 
to allow administrators of the Denodo environment more flexibility 
and control over the codebase. 
This is achieved by splitting up the single exported vql files per database 
into smaller pieces. Possible merge conflicts are more easily located and solved.

# Installation:
Install python3.6 or later from the official python.org
Open command prompt and create a virtual environment "venv" in some folder
where you want the application installed.

on Linux
* python3 -m venv /path/to/new/virtual/environment

on Windows
* python3 -m venv C:\path\to\new\virtual\environment

on Linux activate the virtual environment with:
source /path/to/new/virtual/environment/bin/activate

on Windows activate the virtual environment with:
C:\path\to\new\virtual\environment\Scripts\activate.bat


pip and setuptools will be available in the new environment by default

Install wheel:
* pip install wheel

Install PyQt5 and QDarkStyle.
* pip install PyQt5
* pip install qdarkstyle (or QDarkStyle)

PyQt will install sip as well.

I had to restart my pc before it worked.

# Execution
To run this application just start up the main entry: vqlmanager.py 
Switch to the folder:

* cd C:\path\to\new\virtual\environment

and run the program

* python vqlmanager.py

You can make a link on your desktop to start the app
Start the program from the the environment folder.

# Using the application
The application can be used to support two processes:

1. making selections
2. compare two vql code bases.

Both methods 

 


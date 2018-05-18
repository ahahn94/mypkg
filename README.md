# MYPKG
Helper script for building, installing and removing eopkg 3rd party packages.  

mypkg.py has to be run as root or via the mypkg bash script.

Usage: mypkg [bi] [it] [l] [rm] [cl] [--help]

Options:
<pre>  
 bi      Build package from local pspec.xml file  
 it      Install local package file with the same basename as the working directory  
 l       Launch binary with the same name as the working directory  
 rm      Remove package with the same name as the working directory  
 cl      Delete local package file with the same basename as the working directory  
 --help  Show this helptext  
 </pre>
# MYPKG
Helper script for building, installing and removing eopkg 3rd party packages.  

mypkg.py has to be run as root or via the mypkg bash script.

<pre>
Usage: mypkg [bi] [it] [l] [rm] [cl] [ui] [la] [li] [--help]
       mypkg up LinkToNewArchive Versionnumber

Options:

 bi              Build package from local pspec.xml file.
 it              Install local package file with the same basename as the working directory.
 l               Launch binary with the same name as the working directory.
 rm              Remove package with the same name as the working directory.
 cl              Delete local package file with the same basename as the working directory.
 up              Update the pspec.xml, build and install the package, delete the package file.
 ui              Update installed 3rd party packages.
 li              List installed 3rd party packages.
 la              List available 3rd party packages.
 --help          Show this helptext.

 </pre>
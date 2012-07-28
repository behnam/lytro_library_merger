Lytro Library Merger
====================

Merges all photos of a Lytro library to user's main Lytro library.

Homepage: http://behnam.github.com/lytro_library_merger/

**BACKUP YOUR LYTRO LIBRARY BEFORE RUNNING THIS APPLICATION!**

Given a Lytro photo library, this application merges/imports all
Lytro photos and metadatas from the given library to user's main library,
which is the one that Lytro desktop application uses.

This application does its best to prevent any damage to your photo library
and revent the changes when something goes wrong. But you should not count
on this, so PLEASE BACKUP YOUR LYTRO LIBRARY BEFORE RUNNING THIS APPLICATION!

Run It in Windows 7
-------------------

The only requirement is Python (preferably version 2.7).
If you don't have Python, get the Windows Installer from
http://www.python.org/getit/, run it, and follow the instructions.

Now, download the zipball, upzip it somewhere, and run
`lytro_library_merger.py` from the Windows Explorer by double-cliking on it.
You will be asked to browse to the importing Lytro photo library.

Run It in Max OS X
------------------

Python is installed by default in recent Mac OS X machines.
If you don't have Python, get the Mac OS X Installer from
http://www.python.org/getit/, run it, and follow the instructions.

Now, download the zipball, upzip it somewhere. Select the file
`lytro_library_merger.py` in Finder, click on the `More info...`
button, in section "Open with" select "Python Launcher.app" from
the drop-down list. Close the info box and double-click on the file.
You will be asked to browse to the importing Lytro photo library.

Run It in Command-line
----------------------

In both Windows 7 and Mac OS X, 
you can also run it throw the command-line, setting the importing photo
library path directly. Use `-h` or `--help` to see more options.

*NOTE: command-line support requires Python 2.7.*

Contributing
------------

This application is released under GPLv3 license.  Fork it on GitHub at
https://github.com/behnam/lytro_library_merger

Legal Notice
------------
This program comes with ABSOLUTELY NO WARRANTY; for details
see file COPYING, distributed with this program.
This is free software, and you are welcome to redistribute it
under certain conditions; see file HACKING for details.

Not affiliated with LYTRO, INC.  Lytro (R) is a trademark of LYTRO, INC.
(http://www.lytro.com/)

Copyright (C) 2012  Behnam Esfahbod.
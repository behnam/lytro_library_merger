#!/usr/bin/env python
#
# Lytro Library Merger
# Merges all photos of a Lytro library to user's main Lytro library.
#
# http://behnam.github.com/lytro_library_merger/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2012  Behnam Esfahbod

"""
Merges all photos of a Lytro library to user's main Lytro library.

**BACKUP YOUR LYTRO LIBRARY BEFORE RUNNING THIS APPLICATION!**

Given a Lytro photo library, this application merges/imports all
Lytro photos and metadatas from the given library to user's main library,
which is the one that Lytro desktop application uses.

This application does its best to prevent any damage to your photo library
and revent the changes when something goes wrong. But you should not count
on this, so PLEASE BACKUP YOUR LYTRO LIBRARY BEFORE RUNNING THIS APPLICATION!

Homepage: http://behnam.github.com/lytro_library_merger/

Not affiliated with LYTRO, INC.  Lytro (R) is a trademark of LYTRO, INC.
(http://www.lytro.com/)
"""

import sys
import platform
import sqlite3
import logging
import os, os.path
import shutil


__author__ = "Behnam Esfahbod"
__copyright__ = "Copyright 2012, Behnam Esfahbo"
__credits__ = ["Behnam Esfahbod"]
__license__ = "GPL v3"
__version__ = "1.1"
__maintainer__ = "Behnam Esfahbod"
__email__ = "behnam@esfahbod.info"
__status__ = "Production"


################################################
# Globals

DEBUG   = False
VERBOSE = False
QUIET   = False

PLFM_WIN7 = False
PLFM_OSX  = False

impt_lib_dir = None
main_lib_dir = None


################################################
# Databases

conn1 = conn2 = None

def init_connections ():
    """Check and connect to libraries' databases"""
    global conn1, conn2
    conn1 = make_connection(impt_lib_dir, "importing")
    conn2 = make_connection(main_lib_dir, "main")

def close_connections ():
    close_connection(conn2, main_lib_dir, "Main")
    close_connection(conn1, impt_lib_dir, "Importing")

def make_connection (lib_dir, name):
    try:
        logging.debug("Opening %s library... (%s)", name, lib_dir)
        lib = os.path.join(lib_dir, "library.db")
        if not os.path.exists(lib): raise Exception()
        conn = sqlite3.connect(lib, timeout=2)
        logging.debug("done.")
        return conn
    except:
        raise Exception("Cannot open %s library (%s)" % (name, lib_dir));

def close_connection (conn, lib_dir, name):
    if conn:
        conn.close()
        logging.debug("%s library closed. (%s)", name, lib_dir)

def commit_data ():
    """Commit changes to main database"""
    conn2.commit()

################################################
# Tables

id_map = {}
dup_pids = []
pics = []

def merge_tables ():
    """Merge tables, keep the picture metadata, and find the duplicates"""
    merge_table('events', 5)
    merge_table('import_groups', 1)
    merge_table('imported_pictures', 1,
                new_ids=False,
                error_cb=imported_pictures_error)
    merge_table('pictures', 17,
                pre_update_cb=pictures_pre_update,
                post_update_cb=pictures_post_update)

def merge_table (table_name, num_cols, new_ids=True,
                 pre_update_cb=None,
                 error_cb=None,
                 post_update_cb=None):
    global conn1, conn2
    c1, c2 = conn1.cursor(), conn2.cursor()
    logging.debug("Merging table `%s`..." % table_name)

    # Create queries
    select_sql = "SELECT * FROM %s" % table_name
    insert_sql = ("INSERT INTO %s VALUES (" +
                  ("NULL" if new_ids else "?") +
                  (", ?" * (num_cols-1)) +
                  ")")

    for idx, row in enumerate(c1.execute(select_sql)):
        # Insert data
        id = row[0]
        data = list(row)
        if pre_update_cb and not pre_update_cb(idx, row, data):
            logging.debug("    %s: row skipped (%s)", table_name, id)
            continue
        if new_ids: data = list(data[1:])
        try:
            c2.execute(insert_sql % table_name, data)
        except:
            if error_cb:
                error_cb(idx, row, data)
            logging.debug("    %s: row passed (%s)", table_name, id)
            continue
        # Store new id
        new_id = c2.lastrowid
        if not table_name in id_map: id_map[table_name] = {}
        id_map[table_name][id] = new_id
        if post_update_cb:
            post_update_cb(idx, row, data, new_id)
        # Row done
        if new_ids:
            logging.debug("    %s: row created (%s -> %s)", table_name, id, new_id)
        else:
            logging.debug("    %s: row created (%s)", table_name, id)

    # Table done
    logging.debug("done.")
    c1.close(), c2.close()

def imported_pictures_error(idx, row, data):
    dup_pids.append(idx)

def pictures_pre_update(idx, row, data):
    pid, gid, eid = row[0:3]
    if pid in dup_pids: return False
    data[0:3] = pid, id_map['import_groups'][gid], id_map['events'][eid]
    return True

def pictures_post_update(idx, row, data, new_id):
    pic = dict(pid=row[0], gid=row[1], eid=row[2], name=row[3],
               new_pid=new_id, new_gid=data[0], new_eid=data[1])
    pics.append(pic)
    return True


################################################
# Housekeeping

def housekeeping ():
    """Keeping the new database sane, as much as possible"""
    delete_empty_events()

def delete_empty_events ():
    """Find and remove empty `events` tables,
    cause by possible duplicate files"""
    global conn2
    c2 = conn2.cursor()
    logging.debug("Deleting empty new events...")
    select_sql = """SELECT events.eid, COUNT(pictures.pid) AS cnt
        FROM events
        LEFT OUTER JOIN pictures ON pictures.eid=events.eid
        GROUP BY events.eid HAVING cnt = 0
        """
    new_eids = id_map['events'].values()    
    for idx, row in enumerate(c2.execute(select_sql)):
        new_eid = row[0]
        if new_eid not in new_eids: continue
        c2.execute("DELETE FROM events WHERE eid = ?", (new_eid, ))
        logging.debug("    events: row deleted (%s)", new_eid)

    logging.debug("done.")
    c2.close()

################################################
# Files

copied_files = []
created_dirs = set()

def copy_files ():
    """Merge image and thumbnail files, ignoring duplicates"""
    try:
        logging.debug("Copying LFP files...")
        for pic in pics:
            copy_lfp(pic)
        logging.debug("Copying thumbnail files...")
        for pic in pics:
            copy_tlo(pic)
    except:
        logging.warning("Faced an error! deleting all copied files...")
        delete_files()
        raise

def copy_lfp (pic):
    fr_dir, fr = get_lfp_path(impt_lib_dir, pic, False)
    to_dir, to = get_lfp_path(main_lib_dir, pic, True)
    created_dirs.add(to_dir)
    if not os.path.exists(to_dir):
        os.makedirs(to_dir)
    logging.info("    Copying LFP file (%s, %s -> %s)", pic['pid'], fr, to)
    copied_files.append(to)
    shutil.copyfile(fr, to)

def get_lfp_path (lib_dir, pic, new):
    p = os.path.join(lib_dir, 'images', "%02x" % pic['new_gid' if new else 'gid'])
    return p, os.path.join(p, pic['name'])

def copy_tlo (pic):
    fr_dir, fr = get_tlo_path(impt_lib_dir, pic, False)
    to_dir, to = get_tlo_path(main_lib_dir, pic, True)
    logging.info("    Copying thumbnail file (%s, %s -> %s)", pic['pid'], fr, to)
    copied_files.append(to)
    shutil.copyfile(fr, to)

def get_tlo_path (lib_dir, pic, new):
    p = os.path.join(lib_dir, 'thumbs')
    n = "pic_%05d_lo.jpg" % pic['new_pid' if new else 'pid']
    return p, os.path.join(p, n)


def delete_files ():
    logging.debug("Deleting copied files...")
    for f in copied_files:
        delete_file(f)
    for d in created_dirs:
        delete_dir(d)

def delete_file (f):
    try:
        logging.info("    Deleting file (%s)", f)
        os.remove(f)
    except:
        logging.error("    (Error) Cannot delete file! (%s)", f)

def delete_dir (d):
    try:
        logging.info("    Deleting folder (%s)", d)
        os.rmdir(d)
    except:
        logging.error("    (Error) Cannot delete folder! (%s)", d)


################################################
# Main

def legal_notice():
    output("Lytro Library Merger  Copyright (C) 2012  Behnam Esfahbod")
    output("This program comes with ABSOLUTELY NO WARRANTY; for details")
    output("see file COPYING, distributed with this program.")
    output("This is free software, and you are welcome to redistribute it")
    output("under certain conditions; see file HACKING for details.")
    output()
    output("This application is not affiliated with LYTRO, INC.")
    output("Lytro (R) is a trademark of LYTRO, INC. (http://www.lytro.com/)")
    output()

def main ():
    """The main tasks"""
    try:
        output("(0/4) Checking libraries library...")
        init_connections()
        output("(1/4) Reading data from importing library...")
        merge_tables()
        housekeeping()
        output("(2/4) Copying picature files...")
        copy_files()
        output("(3/4) Writing data to main library...")
        commit_data()
        output("(4/4) Import completed. Enjoy!")
    finally:
        close_connections()

def set_options ():
    """Parse command-line arguments and set logging level"""
    global DEBUG, VERBOSE, QUIET, impt_lib_dir, logging
    # Parse arguments
    try:
        import argparse
        parser = argparse.ArgumentParser(
            #description="Merges a given Lytro library to user's main Lytro library.")
            description=__doc__.splitlines()[1])
        parser.add_argument('-d', '--debug', action='store_true',
                            help='Enable debug mode')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Enable verbose mode')
        parser.add_argument('-q', '--quiet', action='store_true',
                            help='Enable quiet mode')
        parser.add_argument('impt_lib', metavar='importing-library', type=str, nargs='?',
                            help='Path to importing library')
        args = parser.parse_args()
        DEBUG = args.debug
        VERBOSE = args.verbose
        QUIET = args.quiet
        impt_lib_dir = args.impt_lib
    except:
        #TODO fall-back to optparse or manual parsing
        pass
    # Set logging level
    #logging.basicConfig(level=logging.WARNING, format='%(message)s')
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    elif VERBOSE:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    elif QUIET:
        logging.basicConfig(level=logging.ERROR, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

def set_preferences ():
    """Find the directory paths for the libraries, based on the OS"""
    global PLFM_WIN7, PLFM_OSX, main_lib_dir, impt_lib_dir

    PLFM_WIN7 = sys.platform == 'win32'
    PLFM_OSX  = sys.platform == 'darwin'

    # Main library
    if PLFM_WIN7:
        main_lib_dir =  os.path.join(os.environ["LOCALAPPDATA"], "Lytro")
    elif PLFM_OSX:
        main_lib_dir =  os.path.join(os.environ["HOME"], "Pictures", "Lytro.lytrolib")
    else:
        raise Exception("Sorry, your operating system is not supported yet!")

    # Importing library
    if impt_lib_dir:
        dirname = impt_lib_dir
    else:
        if PLFM_WIN7:
            init_dir = os.path.join(os.environ["HOMEPATH"], "Desktop")
        elif PLFM_OSX:
            init_dir = os.path.join(os.environ["HOME"], "Desktop")
        else:
            raise Exception("Sorry, your operating system is not supported yet!")
        try:
            # Open a GUI directory selection dialog
            from Tkinter import Tk
            import tkFileDialog
            toplevel = Tk()
            toplevel.withdraw()
            output('Please browse to the importing library folder.')
            if PLFM_WIN7:
                dirname = tkFileDialog.askdirectory(initialdir=init_dir)
            elif PLFM_OSX:
                dirname = tkFileDialog.askopenfilename(initialdir=init_dir)
        except:
            # Failed by any reason, try asking in the console
            output('Enter path to importing library')
            output('Example: C:\Users\<username>\Desktop\OtherLytro')
            dirname = raw_input('PATH> ')
    impt_lib_dir = os.path.abspath(dirname)
    
    output()
    output('Main library:      %s' % main_lib_dir)
    output('Importing library: %s' % impt_lib_dir)
    output()

def output(text=""):
    if QUIET: return
    print text

def exit (exitcode):
    """Exit, keeping the console window open waiting for user input"""
    if PLFM_WIN7:
        print
        raw_input("Press any key to exit...")
    sys.exit(exitcode)

if __name__=='__main__':
    try:
        set_options()
        legal_notice()
        set_preferences()
        main()
        exit(0)

    except KeyboardInterrupt:
        output("ERROR: Merging intrupted!")
        exit(1)

    except Exception as err:
        if DEBUG:
            logging.exception(err)
        else:
            output("ERROR: %s" % err)
        exit(2)


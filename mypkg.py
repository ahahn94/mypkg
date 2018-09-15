#!/usr/bin/env python3

#
# Copyright (C) 2018  ahahn94
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from sys import argv

import fcntl
import configparser
import datetime
import os
import subprocess
import xml.etree.cElementTree as ET
from os.path import isfile
from subprocess import check_output
from urllib.parse import urlparse


def main(params):
    install_exit_code = 0 # must be 0 (=successfull) for clear to work. prevents deletion of file if install fails.
    if ("--help" in params or len(params) == 0):
        print(HELPTEXT)
        return 0
    if ("up" in params):
        params.remove("up")
        if (len(params) == 3):
            tarball_link = params[0]
            hashsum = params[1]
            version = params[2]
            update(tarball_link, hashsum, version)
        else:
            print(HELPTEXT)
    if ("bi" in params):
        build()
    if ("it" in params):
        install_exit_code = install()
    if ("l" in params):
        launch()
    if ("rm" in params):
        remove()
    if ("cl" in params):
        if (install_exit_code == 0):
            clear()
    return 0


def print_color(options, message):
    """
    Print colorized and formatted text to the bash.
    :param options: List of option strings.
    :param message: Message text.
    :return:
    """
    options = "".join(options)
    print(options + message + NORMAL)


def get_package_name():
    """
    Get package name from directory name.
    :return: Package name.
    """
    return os.path.basename(os.getcwd())


def build():
    """
    Build eopkg package from the pspec.xml file in the working directory.
    :return: Returncode of eopkg or 1 if no pspec.xml file found.
    """
    fileslist = check_output("ls").decode("utf-8").strip().split("\n")
    if (BUILD_CONFIG in fileslist):
        print_color([GREEN, BOLD], HEADER + "Buildconfig found. Initializing build...")
        command = "sudo eopkg bi --ignore-safety pspec.xml"
        return os.system(command)
    else:
        print(HEADER + "No buildconfig found. Aborting")
        return 1


def install():
    """
    Install the eopkg package named like the working directory that lies in the working directory.
    :return: Returncode of eopkg.
    """
    package_name = get_package_name()
    command = "sudo eopkg rm " + package_name + "; sudo eopkg it " + package_name + "*.eopkg"
    print_color([GREEN, BOLD], HEADER + "Trying to acquire filelock...")
    with open("/tmp/mypkg.lock", "w+") as x:
        fcntl.flock(x, fcntl.LOCK_EX)
        print_color([GREEN, BOLD], HEADER + "Lock acquired!")
        print_color([GREEN, BOLD], HEADER + "Installing package " + package_name + "...")
        code = os.system(command)
        print_color([GREEN, BOLD], HEADER + "Releasing filelock...")
        fcntl.flock(x, fcntl.LOCK_UN)
    return code


def remove():
    """
    Remove the eopkg package that is named like the working directory.
    :return: Returncode of eopkg.
    """
    package_name = get_package_name()
    command = "sudo eopkg rm " + package_name
    print_color([GREEN, BOLD], HEADER + "Removing package " + package_name + "...")
    return os.system(command)


def launch():
    """
    Launch the binary that has the same name as the working directory.
    :return: Returncode of the binary.
    """
    package_name = get_package_name()
    command = package_name
    print_color([GREEN, BOLD], HEADER + "Launching " + package_name + "...")
    return os.system(command)

def update(tarball_link, hashsum, version):
    # Check if all necessary files exist
    pspec_file = "pspec.xml"
    actions_file = "actions.py"
    authorfile = "/home/" + os.getenv("SUDO_USER") + "/.solus/packager"
    if (not isfile(actions_file)):
        print_color([RED, BOLD], HEADER + "actions.py not found. Exit!")
        exit(1)
    if (not isfile(pspec_file)):
        print_color([RED, BOLD], HEADER + "pspec.xml not found. Exit!")
        exit(1)
    if (not isfile(authorfile)):
        print_color([RED, BOLD], HEADER + authorfile + " not found. Exit!")
        exit(1)

    # Import author info from YPKG (~/.solus/packager).
    author = configparser.ConfigParser()
    author.read(authorfile)
    name = author["Packager"]["Name"]
    email = author["Packager"]["Email"]

    eopkg_cache = "/var/cache/eopkg/archives"

    print_color([GREEN, BOLD], HEADER + "Starting download...")
    filename = eopkg_cache + "/" + os.path.basename(urlparse(tarball_link).path)
    subprocess.call(["rm", filename])
    subprocess.call(["wget", "-P", eopkg_cache, tarball_link])
    print_color([GREEN, BOLD], HEADER + "Checking hashsum...")
    sha256 = subprocess.getoutput("sha256sum %s" % filename).split()[0].strip()

    if  (sha256 == hashsum):
        # Proceed in updating pspec.xml
        print_color([GREEN, BOLD], HEADER + "Hashsums do match. Calculating SHA1Sum...")
        sha1 = subprocess.getoutput("sha1sum %s" % filename).split()[0].strip()

        # Update pspec.xml
        print_color([GREEN, BOLD], HEADER + "Updating pspec.xml...")
        tree = ET.parse(pspec_file)
        root = tree.getroot()
        archive = root.findall("Source")[0].findall("Archive")[0]
        archive.text = tarball_link
        archive.attrib["sha1sum"] = sha1
        history = root.findall("History")
        last_update = history[0].findall("Update")[0]
        release_number = int(last_update.attrib['release'])
        old_version = str(last_update.findall("Version")[0].text)

        if (version == old_version):
            print("Version is already in history. Exit!\n")
            exit(1)

        release_date = datetime.date.today().strftime("%Y-%m-%d")
        new_release = ET.Element("Update")
        new_release.tail = "\n        "
        new_release.text = "\n            "
        new_release.attrib["release"] = str(release_number+1)
        history[0].insert(0, new_release)
        entry = ET.SubElement(new_release, "Date")
        entry.tail = "\n            "
        entry.text = release_date
        entry = ET.SubElement(new_release, "Version")
        entry.tail = "\n            "
        entry.text = version
        entry = ET.SubElement(new_release, "Comment")
        entry.tail = "\n            "
        entry.text = "Updated to " + version
        entry = ET.SubElement(new_release, "Name")
        entry.tail = "\n            "
        entry.text = name
        entry = ET.SubElement(new_release, "Email")
        entry.tail = "\n            "
        entry.text = email

        lines = ET.tostring(root, 'utf-8').decode().replace("\r\n", "\n").replace("\t", "    ")

        with open(pspec_file, "w") as output_file:
            output_file.writelines(lines)

        print_color([GREEN, BOLD], HEADER + "pspec.xml updated sucessfully!")

        # Build package
        build()
        install()
        clear()

    else:
        print_color([RED, BOLD], HEADER + "Hashsums do not match. Can not proceed")

def clear():
    """
    Remove all eopkg package files from the working directory that have the same name as the directory.
    :return:
    """
    package_name = get_package_name()
    command = "sudo rm " + package_name + "*.eopkg"
    print_color([GREEN, BOLD], HEADER + "Deleting package files from working directory...")
    return os.system(command)


### Constants

# Font-Options
RED = "\033[31m"
ORANGE = "\033[33m"
GREEN = "\033[32m"
BOLD = "\033[1m"
NORMAL = "\033[0m"

# Config File
BUILD_CONFIG = "pspec.xml"

# Line header
HEADER = "[MYPKG] "

# Help text
HELPTEXT = GREEN + BOLD + "\t\t\t\tMYPKG\n" \
                          "Helper script for building, installing and removing eopkg 3rd party packages.\n" \
                          "\t\t\tCopyright (C) 2018 ahahn94\n\n" + NORMAL + "" \
                                                                            "mypkg.py has to be run as root or via the mypkg bash script.\n\n" \
                                                                            "Usage: mypkg [bi] [it] [l] [rm] [cl] [--help]\n" \
                                                                            "       mypkg up LinkToNewArchive SHA256SumOfNewArchive Versionnumber\n\n" \
                                                                            "Options:\n" \
                                                                            " bi\t\t Build package from local pspec.xml file\n" \
                                                                            " it\t\t Install local package file with the same basename as the working directory\n" \
                                                                            " l\t\t Launch binary with the same name as the working directory\n" \
                                                                            " rm\t\t Remove package with the same name as the working directory\n" \
                                                                            " cl\t\t Delete local package file with the same basename as the working directory\n" \
                                                                            " up\t\t Update the pspec.xml, build and install the package, delete the package file\n" \
                                                                            " --help\t\t Show this helptext"

# If not run by root, exit with error message.
if not os.getuid() == 0:
    print_color([RED, BOLD], HEADER + "This program must be run as root!\nAborting")
    exit(1)

params = argv[1:]
main(params)

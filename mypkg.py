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

import os
from subprocess import check_output


def main(params):
    install_exit_code = 0 # must be 0 (=successfull) for clear to work. prevents deletion of file if install fails.
    if ("--help" in params or len(params) == 0):
        print(HELPTEXT)
        return 0
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
    print_color([GREEN, BOLD], HEADER + "Installing package " + package_name + "...")
    return os.system(command)


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
                                                                            "Usage: mypkg [bi] [it] [l] [rm] [cl] [--help]\n\n" \
                                                                            "Options:\n" \
                                                                            " bi\t\t Build package from local pspec.xml file\n" \
                                                                            " it\t\t Install local package file with the same basename as the working directory\n" \
                                                                            " l\t\t Launch binary with the same name as the working directory\n" \
                                                                            " rm\t\t Remove package with the same name as the working directory\n" \
                                                                            " cl\t\t Delete local package file with the same basename as the working directory\n" \
                                                                            " --help\t\t Show this helptext"

# If not run by root, exit with error message.
if not os.getuid() == 0:
    print_color([RED, BOLD], HEADER + "This program must be run as root!\nAborting")
    exit(1)

params = argv[1:]
main(params)

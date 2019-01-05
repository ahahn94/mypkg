#!/usr/bin/env python3

import fcntl
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

import configparser
import datetime
import glob
import os
import subprocess
import xml.etree.cElementTree as ET
from os.path import isdir
from os.path import isfile
from urllib.parse import urlparse

# Mypkg config. Do not change.
mypkg_dir = "/home/" + os.getenv("SUDO_USER") + "/.mypkg"
repo_dir = mypkg_dir + "/3rd-party"
repo_url = "https://github.com/getsolus/3rd-party.git"
mypkg_eopkg_cache = "/home/" + os.getenv("SUDO_USER") + "/.mypkg/cache"  # Cache for generated .eopkg files.


def main(params):
    """
    Main program control.
    :param params: List of the command line arguments.
    :return: 0 if ok.
    """
    init = init_mypkg()
    if (init == 0):
        print_color([GREEN, BOLD], HEADER + "Initialization ok. Proceeding...")
        install_exit_code = 0  # must be 0 (=successfull) for clear to work. prevents deletion of file if install fails.
        working_directory = os.getcwd()  # The options bi it cl rm l and up work on the current working directory.
        if ("--help" in params or len(params) == 0):
            print(HELPTEXT)
            return 0
        if ("la" in params):
            list_available()
            return 0
        if ("li" in params):
            list_installed()
            return 0
        if ("ui" in params):
            update_installed()
            return 0
        if ("up" in params):
            params.remove("up")
            if (len(params) == 2):
                tarball_link = params[0]
                version = params[1]
                update(working_directory, tarball_link, version)
            else:
                print(HELPTEXT)
        if ("bi" in params):
            build(working_directory)
        if ("it" in params):
            install_exit_code = install(working_directory)
        if ("l" in params):
            launch(working_directory)
        if ("rm" in params):
            remove(working_directory)
        if ("cl" in params):
            if (install_exit_code == 0):
                clear(working_directory)
        # Todo: Options for listInstalled, listAvailable
        return 0
    else:
        print_color([RED, BOLD], HEADER + "Initialization failed. Aborting.")
        exit(init)


def print_color(options, message):
    """
    Print colorized and formatted text to the bash.
    :param options: List of option strings.
    :param message: Message text.
    :return: 0 if ok
    """
    options = "".join(options)
    print(options + message + NORMAL)
    return 0


def build(working_directory):
    """
    Build eopkg package from the pspec.xml file in the working directory.
    :param working_directory: Directory that contains the config file.
    :return: Return code of eopkg or 1 if no pspec.xml file found.
    """
    command = "cd " + working_directory + "; ls"
    fileslist = subprocess.getoutput(command).strip().split("\n")
    if (BUILD_CONFIG in fileslist):
        print_color([GREEN, BOLD], HEADER + "Buildconfig found. Initializing build...")
        command = "cd " + mypkg_eopkg_cache + "; sudo eopkg bi --ignore-safety " + working_directory + "/pspec.xml"
        return os.system(command)
    else:
        print(HEADER + "No buildconfig found. Aborting")
        return 1


def install(working_directory):
    """
    Install the eopkg package from the config file that lies in the working directory.
    :return: Return code of eopkg.
    """
    package_name = get_package_name(working_directory + "/pspec.xml")
    command = "sudo eopkg rm " + package_name + "; sudo eopkg it " + mypkg_eopkg_cache + "/" + package_name + "*.eopkg"
    print_color([GREEN, BOLD], HEADER + "Trying to acquire filelock...")
    with open("/tmp/mypkg.lock", "w+") as x:
        fcntl.flock(x, fcntl.LOCK_EX)
        print_color([GREEN, BOLD], HEADER + "Lock acquired!")
        print_color([GREEN, BOLD], HEADER + "Installing package " + package_name + "...")
        code = os.system(command)
        print_color([GREEN, BOLD], HEADER + "Releasing filelock...")
        fcntl.flock(x, fcntl.LOCK_UN)
    return code


def remove(working_directory):
    """
    Remove the eopkg package specified by the config file inside the working directory.
    :param working_directory: Directory that contains the config file.
    :return: Return code of eopkg.
    """
    package_name = get_package_name(working_directory + "/pspec.xml")
    command = "sudo eopkg rm " + package_name
    print_color([GREEN, BOLD], HEADER + "Removing package " + package_name + "...")
    return os.system(command)


def launch(working_directory):
    """
    Launch the binary specified by the config file inside the working directory.
    :param working_directory: Directory that contains the config file.
    :return: Return code of the binary.
    """
    package_name = get_package_name(working_directory + "/pspec.xml")
    command = package_name
    print_color([GREEN, BOLD], HEADER + "Launching " + package_name + "...")
    return os.system(command)


def update(working_directory, tarball_link, version):
    """
    Update the pspec.xml on the working directory to the tarball and version provided.
    :param working_directory: Path to the directory that contains the pspec.xml.
    :param tarball_link: Link to the tarball of the new version.
    :param version: Number of the new version.
    :return: 0 if ok.
    """
    # Check if all necessary files exist.
    pspec_file = working_directory + "/pspec.xml"
    actions_file = working_directory + "/actions.py"
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

    # Download archive.
    eopkg_cache = "/var/cache/eopkg/archives"
    print_color([GREEN, BOLD], HEADER + "Starting download...")
    filename = eopkg_cache + "/" + os.path.basename(urlparse(tarball_link).path)
    subprocess.call(["rm", filename])
    subprocess.call(["wget", "-P", eopkg_cache, tarball_link])

    # Calculate sha1-sum
    print_color([GREEN, BOLD], HEADER + "Calculating SHA1Sum...")
    sha1 = subprocess.getoutput("sha1sum %s" % filename).split()[0].strip()

    # Read data from pspec.xml.
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

    # Check if new version is already the latest update.
    if (version == old_version):
        print("Version is already in history. Exit!\n")
        exit(1)

    # Collect new data.
    release_date = datetime.date.today().strftime("%Y-%m-%d")
    new_release = ET.Element("Update")
    new_release.tail = "\n        "
    new_release.text = "\n            "
    new_release.attrib["release"] = str(release_number + 1)
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

    # Write updated data to pspec.xml.
    lines = ET.tostring(root, 'utf-8').decode().replace("\r\n", "\n").replace("\t", "    ")
    with open(pspec_file, "w") as output_file:
        output_file.writelines(lines)

    print_color([GREEN, BOLD], HEADER + "pspec.xml updated sucessfully!")

    # Build and install package. Clean up after install.
    build(working_directory)
    install(working_directory)
    clear(working_directory)


def clear(working_directory):
    """
    Remove all eopkg files from ~/.mypkg/cache that have the same name as the package from the working directory.
    :param working_directory: Directory that contains the config file.
    :return:
    """
    package_name = get_package_name(working_directory + "/pspec.xml")
    command = "cd " + mypkg_eopkg_cache + "; sudo rm " + package_name + "*.eopkg"
    print_color([GREEN, BOLD], HEADER + "Deleting package files from working directory...")
    return os.system(command)


def update_installed():
    """
    Update all installed packages that are on the 3rd party repo.
    :return: 0 if ok.
    """
    # Get dict of available 3rd party packages, their paths and current release number from repo.
    available_packages = get_available_packages()

    # Get dict of installed packages from eopkg.
    installed_packages = get_installed_packages(available_packages)

    # Get details about the packages (release number).
    installed_packages_details = {}
    for package in installed_packages:
        command = "eopkg info " + package
        installed_release = subprocess.getoutput(command).split("\n")[1].split(" ")[-1]  # Last item of second line.
        installed_packages_details[package] = {'release': installed_release}

    # Select packages for update.
    update_candidates = []
    for package in installed_packages:
        if (installed_packages_details[package]['release'] < available_packages[package]['release']):
            update_candidates.append(package)

    # Ready for updates. Ask to proceed.
    if (len(update_candidates) != 0):
        print_color([GREEN, BOLD], HEADER + "The following packages will be upgraded:")
        print(", ".join(update_candidates))
        selection_successful = False
        while (not selection_successful):
            selection = input(GREEN + BOLD + HEADER + "Do you want to continue? (y/n)" + NORMAL)
            if (selection == "y"):
                # Proceed to build and install updates.
                selection_successful = True
            elif (selection == "n"):
                # Exit program.
                exit(0)
            # Else ask again.
        print_color([GREEN, BOLD], HEADER + "Starting upgrades...")

        # Build and install updates.
        for package in update_candidates:
            working_directory = available_packages[package]['config']
            build(working_directory)
            install(working_directory)
            clear(working_directory)
        return 0
    else:
        print_color([GREEN, BOLD], HEADER + "No packages to upgrade.")
        return 0


def list_available():
    """
    List packages that are available on the 3rd party repo.
    :return: 0 if ok.
    """
    available_packages = list(get_available_packages().keys())
    available_packages.sort()
    print_color([GREEN, BOLD], "Available packages:")
    print("\n".join(available_packages))
    return 0


def list_installed():
    """
    List installed packages that are from the 3rd party repo.
    :return: 0 if ok.
    """
    installed_packages = get_installed_packages(get_available_packages())
    installed_packages.sort()
    print_color([GREEN, BOLD], "Installed packages:")
    print("\n".join(installed_packages))
    return 0


def get_available_packages():
    """
    Get dict of available 3rd party packages, their paths and current release number from repo.
    :return: dict of the available packages.
    """
    available_packages = {}
    for filepath in glob.glob(repo_dir + '/**/pspec.xml', recursive=True):
        package_name_and_release = get_package_name_and_release(filepath)
        package_config = os.path.dirname(filepath)
        package_name = package_name_and_release['name']
        package_release = package_name_and_release['release']
        package_details = {'config': package_config, 'release': package_release}
        available_packages[package_name] = package_details
    return available_packages


def get_installed_packages(available_packages):
    """
    Get list of installed packages from eopkg.
    :param available_packages: Dict of available packages (from get_available_packages).
    :return: List of the installed packages.
    """
    command = "eopkg li | awk '{print $1; }'"
    all_installed_packages = subprocess.getoutput(command).split("\n")
    # Reduce list to packages from the 3rd party repo.
    available_packages_names = list(available_packages.keys())
    installed_packages = list(set(available_packages_names) & set(all_installed_packages))
    return installed_packages


def get_package_name(filepath):
    """
    Read the package name from the pspec.xml specified by filepath.
    :param filepath: Path to pspec.xml.
    :return: Package name.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()
    return root.findall("Package")[0].findall("Name")[0].text


def get_package_name_and_release(filepath):
    """
    Read the package name and the release number from the pspec.xml specified by filepath.
    :param filepath: Path to pspec.xml.
    :return: Package name and release as dict.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()
    package_name = root.findall("Package")[0].findall("Name")[0].text
    package_release = root.findall("History")[0].findall("Update")[0].attrib['release']
    return {'name': package_name, 'release': package_release}


def init_mypkg():
    """
    Init ~/.mypkg. Download or update local copy of the github repo.
    :return: 0 if ok.
    """
    print_color([GREEN, BOLD], HEADER + "Checking initialization of " + mypkg_dir + "...")
    return_code = 0
    if (isdir(mypkg_dir)):
        if (isdir(repo_dir)):
            # Repo already exists. Pull update.
            return_code += update_repo()
        else:
            # ~/.mypkg exists, but the repo has not yet been cloned. Clone repo.
            return_code += init_repo()
        if (not isdir(mypkg_eopkg_cache)):
            return_code += init_cache()
        return return_code
    else:
        # ~/.mypkg does not exist. Create .mypkg and clone repo. Create cache.
        command = "mkdir " + mypkg_dir + "; mkdir " + mypkg_eopkg_cache + ";cd " + mypkg_dir + "; git clone " + repo_url
        return os.system(command)


def init_cache():
    """
    Create ~/.mypkg/cache.
    :return: Return code from the mkdir command. 0 if ok.
    """
    command = "mkdir -p " + mypkg_eopkg_cache
    return os.system(command)


def init_repo():
    """
    Create ~/.mypkg if necessary and clone the 3rd party Github repo.
    :return: Return code from the mkdir and git commands. 0 if ok.
    """
    command = "mkdir " + mypkg_dir + "; cd " + mypkg_dir + "; git clone " + repo_url
    return os.system(command)


def update_repo():
    """
    Update the local copy of the 3rd party Github repo.
    :return: Return code from the git command. 0 if ok.
    """
    command = "cd " + repo_dir + "; git pull origin master"
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
                                                                            "Usage: mypkg [bi] [it] [l] [rm] [cl] [ui] [la] [li] [--help]\n" \
                                                                            "       mypkg up LinkToNewArchive Versionnumber\n\n" \
                                                                            "Options:\n" \
                                                                            " bi\t\t Build package from local pspec.xml file.\n" \
                                                                            " it\t\t Install local package file specified by pspec.xml in working directory.\n" \
                                                                            " l\t\t Launch binary specified by pspec.xml in working directory.\n" \
                                                                            " rm\t\t Remove package specified by pspec.xml in working directory.\n" \
                                                                            " cl\t\t Delete local package file specified by pspec.xml in working directory.\n" \
                                                                            " up\t\t Update the pspec.xml, build and install the package, delete the package file.\n" \
                                                                            " ui\t\t Update installed 3rd party packages.\n" \
                                                                            " li\t\t List installed 3rd party packages.\n" \
                                                                            " la\t\t List available 3rd party packages.\n" \
                                                                            " --help\t\t Show this helptext." # Todo: Update help text.

# If not run by root, exit with error message.
if not os.getuid() == 0:
    print_color([RED, BOLD], HEADER + "This program must be run as root!\nAborting")
    exit(1)

params = argv[1:]
main(params)

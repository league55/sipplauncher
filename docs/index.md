![Logo](assets/images/logo.png)

# **sipplauncher** - automate your VoIP testing

- Execute your [SIPp](http://sipp.sourceforge.net) testsuite with just **one command** in one VM/container.
- Easily add SIP traffic testing to your **continuos integration pipeline**.
- Run **multiple test scenarios** at the same time. Highly-configurable.

----

- Automatically generate pcap files for each test.
- Ability to provision and/or clean-up the device under test using BASH scripts.
- sipplauncher uses HP SIPp.
- sipplauncher accepts a path to a folder. If the folder contains at least one
SIPp scenario file, will try to run such scenario only. If folder does not
contain scenario files, all subfolders containing scenario files will be
processed.
- Scenario's parent folder will be used as scenario name.
- Accepted scenario file names are "(uas|uac)_role.xml".
- User Agents whose file name contains "uas" prefix will be launched first.
- Scenario files may contain references to other UA's address in the form role.host.

----

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs help` - Print this help message.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

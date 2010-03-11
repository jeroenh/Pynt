# -*- coding: utf-8 -*-
"""Reads local file with usernames and passwords"""

import ConfigParser
import getpass      # interactive password asking
try:
    import readline     # enhances raw_input() function
except ImportError:
    pass                # no big deal if it doesn't work

def GetLoginSettings(hostname, username="", password="", configfile="usernames.cfg", interactive=True):
    """Given a hostname, returns username and password."""
    config = ConfigParser.ConfigParser()
    # WARNING: it does not seem possible to set the input encoding of ConfigParser
    result = config.read(configfile)  # walks sys.path
    if len(result) > 0:
        try:
            if not username:
                username = config.get(hostname, 'username')
            if not password:
                password = config.get(hostname, 'password')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError, ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError):
            raise
    elif interactive:
        print _gethelptext(hostname, username, password)
        username = getpass.getuser()
        userinput = raw_input("Username for %s [%s]:" % (hostname, username))
        if userinput.isalnum():
            username = userinput
        elif userinput != "":
            print "Ignoring username input: it contains non alfa-numeric characters"
        password = getpass.getpass("Password for %s@%s:" % (username, hostname))
        if not password.isalnum():
            print "Ignoring password input: it contains non alfa-numeric characters"
            password = ""
    else:
        raise Exception(("Do not know username and password for %s.\n"+_gethelptext(hostname, username, password)) % hostname)
    return {"username": username, "password": password}

def _gethelptext(hostname, username="", password=""):
    return "Create a file usernames.cfg with the following content to avoid manual specification:\n" + \
           "[%s]\n" % hostname + \
           "username = %s\n" % username + \
           "password = %s\n" % password

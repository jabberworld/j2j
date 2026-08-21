#!/usr/bin/env python3
# J2J - Jabber-To-Jabber component
# http://JRuDevels.org
# http://wiki.JRuDevels.org
#
# copyright 2007 Dobrov Sergey aka Binary from JRuDevels
#
# License: GPL-v3

import argparse
import os
import signal
import sys

from config import Config
import j2j

__id__ = "$Id: main.py 149 2011-02-10 13:32:52Z binary $"


def daemonize():
    """Simple double-fork daemonization (POSIX)."""
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.chdir("/")
    os.umask(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)


def main():
    __all__ = ['j2j', 'client', 'database', 'roster',
               'utils', 'adhoc', 'debug', 'config']
    revision = 0
    date = 0

    parser = argparse.ArgumentParser(
        prog='j2j',
        description='Jabber-To-Jabber component')
    parser.add_argument('-c', '--config', metavar='FILE',
                        dest='configFile',
                        help="Read config from custom file")
    parser.add_argument('-b', '--background', dest='configBackground',
                        help="Daemonize/background transport",
                        action="store_true")
    options = parser.parse_args()

    try:
        modRev = int(__id__.split(" ")[2])
        modDate = int(__id__.split(" ")[3].replace("-", ""))
    except (ValueError, IndexError):
        modRev = 0
        modDate = 0

    if modRev > revision:
        revision = modRev
    if modDate > date:
        date = modDate

    for modName in __all__:
        module = __import__(modName, globals(), locals())
        try:
            modRev = int(module.__id__.split(" ")[2])
            modDate = int(module.__id__.split(" ")[3].replace("-", ""))
        except (AttributeError, ValueError, IndexError):
            modRev = 0
            modDate = 0
        if modRev > revision:
            revision = modRev
        if modDate > date:
            date = modDate

    if revision == 0:
        revision = ''
    else:
        revision = '.r' + str(revision)
    if date != 0:
        date = str(date)
        revision = revision + " %s-%s-%s" % (date[:4], date[4:6],
                                             date[6:8])

    version = "1.2.10" + revision

    if options.configFile:
        config = Config(options.configFile)
    else:
        config = Config()

    if options.configBackground and os.name == "posix":
        daemonize()

    if config.PROCESS_PID:
        with open(config.PROCESS_PID, "w") as pidfile:
            pidfile.write("%s\n" % os.getpid())

    c = j2j.J2JComponent(version, config, config.JID)
    c.connect()
    loop = c.loop
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, c.shutdownHandler)
        except NotImplementedError:
            signal.signal(sig, c.shutdownHandler)
    loop.run_forever()


if __name__ == "__main__":
    main()
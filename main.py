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

    version = "2.0.0"

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
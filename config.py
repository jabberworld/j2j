# Part of J2J (http://JRuDevels.org)
# Copyright 2008 JRuDevels.org

# Python3 / slixmpp port of the J2J transport.

import configparser
import os

import i18n

def config_decorator(func):
    def wrapper(section, option, default=None, required=False):
        try:
            return func(section, option)
        except (configparser.NoOptionError, configparser.NoSectionError):
            if required:
                raise
            return default
    return wrapper

class Config:

    def __init__(self, configname=["j2j.conf",
                                   os.path.expanduser("~/.j2j/j2j.conf"),
                                   "/etc/j2j/j2j.conf"]):
        config = configparser.ConfigParser(
            inline_comment_prefixes=(';', '#'))
        config.read(configname)

        get = config_decorator(config.get)
        getboolean = config_decorator(config.getboolean)

        raw_lang = get("general", "default_language",
                       default=i18n.DEFAULT).strip()
        self.DEFAULT_LANGUAGE = i18n.normalize(raw_lang)
        if self.DEFAULT_LANGUAGE != raw_lang.lower().split('-', 1)[0]:
            raise ValueError(
                "Invalid [general] default_language %r: must be one "
                "of %s" % (raw_lang, ", ".join(i18n.LANGUAGES)))

        self.JID = get("component", "JID", required=True)
        self.HOST = get("component", "Host", required=True)
        self.PORT = int(get("component", "Port", required=True))
        self.PASSWORD = get("component", "Password", required=True)
        self.SEND_PROBES = getboolean("component", "Send_probes", default=True)

        self.PROCESS_PID = get("process", "Pid")

        self.DB_NAME = get("database", "Name", required=True)

        self.DEBUG_REGISTRATIONS = getboolean("debug", "registrations",
                                              default=False)
        self.DEBUG_LOGINS = getboolean("debug", "logins", default=False)
        # No logfile -> log to console (stderr).
        self.LOGFILE = get("debug", "logfile")

        levels = ("debug", "info", "warning", "error", "critical")
        self.LOGLEVEL = get("debug", "loglevel", default="info").lower()
        if self.LOGLEVEL not in levels:
            raise ValueError(
                "Invalid [debug] loglevel %r: must be one of %s" %
                (self.LOGLEVEL, ", ".join(levels)))

        self.DEBUG_COMPXML = getboolean("debug", "component_xml",
                                        default=False)
        self.DEBUG_CLXML = getboolean("debug", "clients_xml", default=False)
        self.DEBUG_CLXMLACL = get("debug", "clients_jids_to_log", default='')

        admins = get("admins", "List", default="")
        self.ADMINS = admins.split(",")
        self.ADMINS = [admin for admin in self.ADMINS if admin]
        self.REGISTRATION_NOTIFY = getboolean("admins",
                                              "Registrations_notify",
                                              default=True)
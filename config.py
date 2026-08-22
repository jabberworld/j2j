# Part of J2J (http://JRuDevels.org)
# Copyright 2008 JRuDevels.org

# Python3 / slixmpp port of the J2J transport.

import configparser
import os
import re

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
        # Remember which file the configuration was loaded from so
        # runtime changes (e.g. the admin "set default language"
        # command) can be persisted.
        candidates = ([configname] if isinstance(configname, str)
                      else list(configname))
        self.config_file = next(
            (p for p in candidates if os.path.exists(p)), None)

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
        # Default roster import mechanism preselected in the
        # registration form: off / subscribe / rosterx / auto.
        # "auto" probes the client for XEP-0144 roster item exchange
        # support and offers it when announced, otherwise no import.
        raw_mode = get("general", "import_mode", default="auto").strip()
        modes = ("off", "subscribe", "rosterx", "auto")
        if raw_mode.lower() not in modes:
            raise ValueError(
                "Invalid [general] import_mode %r: must be one of %s"
                % (raw_mode, ", ".join(modes)))
        self.IMPORT_MODE = raw_mode.lower()
        # Roster group offered to users for imported contacts
        # (pre-filled, still editable per user in the form).
        self.ROSTER_GROUP_NAME = get("general", "roster_group_name",
                                     default="Контакты j2j").strip()
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
        # Strip whitespace so "a@x.org, b@y.org" matches bare JIDs.
        self.ADMINS = [admin.strip() for admin in admins.split(",")
                       if admin.strip()]
        self.REGISTRATION_NOTIFY = getboolean("admins",
                                              "Registrations_notify",
                                              default=True)

    def setDefaultLanguage(self, lang):
        """Change the transport-wide default language: update the
        in-memory value and persist it to the config file."""
        lang = i18n.normalize(lang)
        self.DEFAULT_LANGUAGE = lang
        return self._persistOption("default_language", lang)

    def setImportMode(self, mode):
        """Change the default roster import mechanism; *mode* is one
        of off / subscribe / rosterx / auto."""
        modes = ("off", "subscribe", "rosterx", "auto")
        if mode not in modes:
            raise ValueError(
                "Invalid import_mode %r: must be one of %s"
                % (mode, ", ".join(modes)))
        self.IMPORT_MODE = mode
        return self._persistOption("import_mode", mode)

    def setRosterGroupName(self, name):
        """Change the default roster group name for imported
        contacts."""
        self.ROSTER_GROUP_NAME = name.strip()
        if not self.ROSTER_GROUP_NAME:
            self.ROSTER_GROUP_NAME = "Контакты j2j"
        return self._persistOption("roster_group_name",
                                   self.ROSTER_GROUP_NAME)

    def _persistOption(self, option, value, section="general"):
        """Persist a single option to the config file by replacing
        only its line (all other lines, comments included, are
        preserved). Returns False when the config file path is
        unknown."""
        if not self.config_file:
            return False
        with open(self.config_file, encoding='utf-8') as f:
            lines = f.readlines()
        option_re = re.compile(
            r'(?i)^(\s*)%s\s*[=:].*$' % re.escape(option))
        out = []
        done = False
        in_section = False
        section_at = None
        header = "[%s]" % section
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                in_section = stripped.lower() == header.lower()
                if in_section:
                    section_at = len(out)
            if in_section and not done and \
               option_re.match(line.rstrip('\n')):
                out.append('%s=%s\n' % (option, value))
                done = True
                continue
            out.append(line)
        if not done:
            if section_at is not None:
                # Section exists without the option: insert right
                # after the section header.
                out.insert(section_at + 1, '%s=%s\n' % (option, value))
            else:
                if out and not out[-1].endswith('\n'):
                    out[-1] += '\n'
                out += ['\n', '%s\n' % header, '%s=%s\n'
                        % (option, value)]
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.writelines(out)
        return True
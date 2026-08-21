import logging
import time

class Debug:
    """Logging facade for the transport.

    All messages go through a single sink: the file configured in the
    [debug] section or, when no logfile is set, stderr. Messages carry a
    severity (DEBUG/INFO/WARNING/ERROR/CRITICAL) shown in every record;
    the configured loglevel hides everything below it.
    """

    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(self, logFile, registrations, logins, componentXmlLog,
                 clientsXmlLog, clientJidsToLog, loglevel="info"):
        self.registrations = registrations
        self.logins = logins
        self.componentXmlLog = componentXmlLog
        self.clientsXmlLog = clientsXmlLog
        self.clientJidsToLog = clientJidsToLog
        self.clAcl = clientJidsToLog.split(",")

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            "%Y/%m/%d %H:%M:%S")
        if logFile:
            handler = logging.FileHandler(logFile)
        else:
            handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        # One shared pipeline for transport messages and slixmpp's own
        # internal logging.
        root = logging.getLogger()
        root.addHandler(handler)
        level = self.LEVELS[loglevel]
        root.setLevel(level)
        self.logger = logging.getLogger("j2j")

    def getTheTime(self):
        return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(time.time()))

    def registrationsLog(self, message):
        if self.registrations:
            self.logger.info(message)

    def loginsLog(self, message):
        if self.logins:
            self.logger.info(message)

    def loginConflictLog(self, message):
        if self.logins:
            self.logger.warning(message)

    def loginErrorLog(self, message):
        if self.logins:
            self.logger.error(message)

    def componentXmlsLog(self, data, out=False):
        if self.componentXmlLog:
            if isinstance(data, bytes):
                data = data.decode("utf-8", "replace")
            arrow = out and ">>>" or "<<<"
            self.logger.debug("%s Component\n%s", arrow, data.rstrip("\n"))

    def clientsXmlsLog(self, data, jid, hjid, out=False):
        if self.clientsXmlLog and \
           (hjid.bare in self.clAcl or self.clAcl == ["All"]):
            if isinstance(data, bytes):
                data = data.decode("utf-8", "replace")
            arrow = out and ">>>" or "<<<"
            self.logger.debug("%s Client %s, host %s\n%s",
                              arrow, jid.full, hjid.full, data.rstrip("\n"))

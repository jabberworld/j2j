# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port: sqlite3 backend.

import logging
import sqlite3

import dbcrypto

log = logging.getLogger(__name__)

class StartupError(RuntimeError):
    """Fatal configuration/database mismatch at startup."""

class Database:
    def __init__(self, config):
        self.config = config
        self.db = sqlite3.connect(config.DB_NAME)
        self.dbCursor = self.db.cursor()
        self._initSchema()
        self._cryptoKey = None
        self._initCrypto()

    def __del__(self):
        try:
            if self.dbCursor:
                self.dbCursor.close()
            if self.db:
                self.db.close()
        except Exception:
            pass

    def _initSchema(self):
        self.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " jid TEXT UNIQUE,"
            " username TEXT,"
            " domain TEXT,"
            " server TEXT,"
            " password TEXT,"
            " port INTEGER,"
            " import_roster INTEGER DEFAULT 0,"
            " remove_from_guest_roster INTEGER DEFAULT 0,"
            " import_group TEXT)")
        self.execute(
            "CREATE TABLE IF NOT EXISTS rosters ("
            " user_id INTEGER,"
            " jid TEXT)")
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_rosters_user_id "
            "ON rosters (user_id)")
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_rosters_user_jid "
            "ON rosters (user_id, jid)")
        self.execute(
            "CREATE TABLE IF NOT EXISTS users_options ("
            " user_id INTEGER UNIQUE,"
            " replytext TEXT,"
            " autoreplybutforward INTEGER DEFAULT 0,"
            " onlyroster INTEGER DEFAULT 0,"
            " autoreplyenabled INTEGER DEFAULT 0,"
            " language TEXT,"
            " disabled INTEGER DEFAULT 0,"
            " rostersync INTEGER DEFAULT 1)")
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_options_user_id "
            "ON users_options (user_id)")
        # Migration for databases created before the language/disabled
        # columns existed (CREATE TABLE IF NOT EXISTS does not alter
        # old files).
        cols = [row[1] for row in
                self.fetchall("PRAGMA table_info(users_options)")]
        if 'language' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN language TEXT")
        if 'disabled' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN "
                "disabled INTEGER DEFAULT 0")
        if 'notify_typing' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN "
                "notify_typing INTEGER DEFAULT 1")
        if 'notify_activity' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN "
                "notify_activity INTEGER DEFAULT 1")
        if 'notify_receipts' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN "
                "notify_receipts INTEGER DEFAULT 1")
        if 'rostersync' not in cols:
            self.execute(
                "ALTER TABLE users_options ADD COLUMN "
                "rostersync INTEGER DEFAULT 1")
        ucols = [row[1] for row in
                 self.fetchall("PRAGMA table_info(users)")]
        if 'import_group' not in ucols:
            self.execute(
                "ALTER TABLE users ADD COLUMN import_group TEXT")
        # Master-password metadata: per-database KDF salt.
        self.execute(
            "CREATE TABLE IF NOT EXISTS crypto_meta ("
            " key TEXT PRIMARY KEY,"
            " value TEXT)")
        self.commit()

    def _initCrypto(self):
        """Prepare password encryption: derive the Fernet key from the
        configured master password, migrate legacy plaintext rows in
        place and refuse to start on obvious master/config mismatch."""
        master = getattr(self.config, 'MASTER_PASSWORD', '') or ''
        encrypted = self.getCount(
            "users", "password LIKE ?",
            (dbcrypto.PREFIX + '%',))
        if not master:
            if encrypted:
                raise StartupError(
                    "%d password(s) in the database are encrypted but "
                    "[database] master_password is not configured" %
                    encrypted)
            return
        salt = None
        row = self.fetchone(
            "SELECT value FROM crypto_meta WHERE key='kdf_salt'")
        if row is not None:
            salt = row[0]
        if not salt:
            salt = dbcrypto.generate_salt()
            self.execute(
                "INSERT INTO crypto_meta (key,value) "
                "VALUES ('kdf_salt',?)", (salt,))
            self.commit()
        self._cryptoKey = dbcrypto.derive_key(master, salt)
        # One-time migration of plaintext passwords written before the
        # feature existed (or while no master password was set).
        rows = self.fetchall(
            "SELECT id,password FROM users WHERE password IS NOT NULL "
            "AND password != '' AND password NOT LIKE ?",
            (dbcrypto.PREFIX + '%',))
        for uid, password in rows:
            self.execute(
                "UPDATE users SET password=? WHERE id=?",
                (self.encryptPassword(password), str(uid)))
        if rows:
            self.commit()
            log.info("Encrypted %d password(s) in the database", len(rows))
        if encrypted:
            # Fail fast on a wrong master password instead of failing
            # later at guest login time.
            stored = self.fetchone(
                "SELECT password FROM users WHERE password LIKE ? "
                "LIMIT 1", (dbcrypto.PREFIX + '%',))[0]
            try:
                dbcrypto.decrypt(self._cryptoKey, stored)
            except dbcrypto.CryptoError:
                raise StartupError(
                    "Master password does not match the database")

    def encryptPassword(self, password):
        """Encrypt *password* with the configured master password; a
        no-op (passthrough) when encryption is disabled."""
        if not self._cryptoKey or not password:
            return password
        return dbcrypto.encrypt(self._cryptoKey, password)

    def _decryptPassword(self, stored):
        if not stored or not self._cryptoKey or \
                not dbcrypto.looks_encrypted(stored):
            return stored
        try:
            return dbcrypto.decrypt(self._cryptoKey, stored)
        except dbcrypto.CryptoError as exc:
            raise RuntimeError(
                "Cannot decrypt a stored password: %s" % exc)

    def execute(self, query, params=()):
        self.dbCursor.execute(query, params)

    def fetchone(self, query, params=()):
        self.execute(query, params)
        row = self.dbCursor.fetchone()
        if row is None:
            return row
        return list(row)

    def fetchall(self, query, params=()):
        self.execute(query, params)
        return self.dbCursor.fetchall()

    def commit(self):
        self.db.commit()

    def getCount(self, table, where='', params=()):
        if where:
            where = 'WHERE ' + where
        return self.fetchone(
            'SELECT count(*) FROM %s %s' % (table, where), params)[0]

    def getIdByJid(self, qjid):
        row = self.fetchone(
            'SELECT id FROM users WHERE jid=?', (qjid,))
        if row is None:
            return row
        return row[0]

    def getDataById(self, uid):
        data = self.fetchone(
            "SELECT username,password,domain,"
            "server,port,import_roster,"
            "remove_from_guest_roster,import_group FROM "
            "users WHERE id=?", (uid,))
        if data is not None:
            # Stored encrypted when a master password is configured;
            # callers always see the plaintext.
            data[1] = self._decryptPassword(data[1])
        return data

    def getOptsById(self, uid):
        """Options tuple: [replytext, autoreplybutforward, onlyroster,
        autoreplyenabled, language, disabled, remove_from_guest_roster,
        notify_typing, notify_activity, notify_receipts, rostersync]
        (remove_from_guest_roster lives in the users table, the rest in
        users_options). rostersync defaults to 1 (sync on login)."""
        data = self.fetchone(
            'SELECT o.replytext,o.autoreplybutforward,'
            'o.onlyroster,o.autoreplyenabled,o.language,o.disabled,'
            'u.remove_from_guest_roster,o.notify_typing,'
            'o.notify_activity,o.notify_receipts,o.rostersync FROM '
            'users_options o JOIN users u ON u.id=o.user_id '
            'WHERE o.user_id=?', (uid,))
        if data[0] is None:
            data[0] = ''
        if len(data) > 10 and data[10] is None:
            data[10] = 1
        return data

    def getLangById(self, uid):
        row = self.fetchone(
            'SELECT language FROM users_options WHERE user_id=?',
            (uid,))
        if row is None:
            return None
        return row[0]

    def setLangById(self, uid, lang):
        self.execute(
            'UPDATE users_options SET language=? WHERE user_id=?',
            (lang, str(uid)))

    def isDisabled(self, uid):
        """True when the account is suspended (missing options row or
        legacy NULL count as enabled)."""
        row = self.fetchone(
            'SELECT disabled FROM users_options WHERE user_id=?',
            (uid,))
        if row is None:
            return False
        return bool(row[0])

    def setDisabled(self, uid, flag):
        self.execute(
            'UPDATE users_options SET disabled=? WHERE user_id=?',
            (int(bool(flag)), str(uid)))

    def setRemoveFromGuestRoster(self, uid, flag):
        self.execute(
            'UPDATE users SET remove_from_guest_roster=? WHERE id=?',
            (int(bool(flag)), str(uid)))

    def activeUserJids(self):
        """Bare JIDs of registered, non-suspended users."""
        rows = self.fetchall(
            'SELECT u.jid FROM users u '
            'LEFT JOIN users_options o ON o.user_id=u.id '
            'WHERE COALESCE(o.disabled,0)=0')
        return [jid for (jid,) in rows]
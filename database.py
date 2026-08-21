# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port: sqlite3 backend.

import os
import sqlite3

class Database:
    def __init__(self, config):
        self.config = config
        self.db = sqlite3.connect(config.DB_NAME)
        self.dbCursor = self.db.cursor()
        self._initSchema()

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
            " remove_from_guest_roster INTEGER DEFAULT 0)")
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
            " disabled INTEGER DEFAULT 0)")
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
        self.commit()

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
        return self.fetchone(
            "SELECT username,password,domain,"
            "server,port,import_roster,"
            "remove_from_guest_roster FROM "
            "users WHERE id=?", (uid,))

    def getOptsById(self, uid):
        data = self.fetchone(
            'SELECT replytext,autoreplybutforward,'
            'onlyroster,autoreplyenabled,language,disabled FROM '
            'users_options WHERE user_id=?', (uid,))
        if data[0] is None:
            data[0] = ''
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

    def activeUserJids(self):
        """Bare JIDs of registered, non-suspended users."""
        rows = self.fetchall(
            'SELECT u.jid FROM users u '
            'LEFT JOIN users_options o ON o.user_id=u.id '
            'WHERE COALESCE(o.disabled,0)=0')
        return [jid for (jid,) in rows]
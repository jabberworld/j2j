# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the J2J gateway component.

import copy
import hashlib
import platform
import time

import slixmpp
from slixmpp import ComponentXMPP
from slixmpp.jid import InvalidJID, JID
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath

import utils
import database
import debug
import i18n
from client import GuestClient
from adhoc import AdHoc

class J2JComponent(ComponentXMPP):
    def __init__(self, version, config, cJid):
        ComponentXMPP.__init__(self, str(cJid), config.PASSWORD,
                               host=config.HOST, port=config.PORT,
                               plugin_config={},
                               plugin_whitelist=[])
        self.config = config
        self.adhoc = AdHoc(self)
        self.VERSION = version
        self.cJid = str(cJid)
        self.clients = {}
        self.shuttingDown = False
        self.restartRequested = False
        self.startTime = 0
        self.debug = debug.Debug(
            config.LOGFILE,
            config.DEBUG_REGISTRATIONS,
            config.DEBUG_LOGINS,
            config.DEBUG_COMPXML,
            config.DEBUG_CLXML,
            config.DEBUG_CLXMLACL,
            config.LOGLEVEL)
        self.db = database.Database(config)

        self.add_event_handler('session_start', self.componentConnected)
        self.register_handler(
            Callback('J2JPresence', StanzaPath('presence'), self.onPresence))
        self.register_handler(
            Callback('J2JMessage', StanzaPath('message'), self.onMessage))
        self.register_handler(
            Callback('J2JIq', StanzaPath('iq'), self.onIq))

    # ---- i18n ----

    def effectiveLang(self, stored):
        """Map a stored per-user language (possibly None) onto a
        supported code, falling back to the transport default."""
        if stored:
            return i18n.normalize(stored)
        return self.config.DEFAULT_LANGUAGE

    def getUserLang(self, bare_jid):
        uid = self.db.getIdByJid(bare_jid)
        if uid:
            return self.effectiveLang(self.db.getLangById(uid))
        return self.config.DEFAULT_LANGUAGE

    def componentConnected(self, event=None):
        self.shuttingDown = False
        self.startTime = time.time()
        if self.config.SEND_PROBES:
            for jid in self.db.activeUserJids():
                self.send_presence(ptype='probe', pto=jid,
                                   pfrom=self.cJid)
        self.debug.logger.info("Connected to server, service available at %s",
                               self.cJid)

    # ---- XML debug logging ----

    def incoming_filter(self, xml):
        if getattr(self, 'debug', None):
            self.debug.componentXmlsLog(utils.tostring(xml))
        return ComponentXMPP.incoming_filter(self, xml)

    def send_raw(self, data):
        if not self.startTime:
            return ComponentXMPP.send_raw(self, data)
        self.debug.componentXmlsLog(data, out=True)
        return ComponentXMPP.send_raw(self, data)

    # ---- message routing ----

    def onMessage(self, el):
        fro = el['from']
        to = el['to']
        try:
            fro = JID(fro)
            to = JID(to)
        except InvalidJID:
            return
        if to.full == self.cJid:
            return
        if fro.full in self.clients and \
           self.clients[fro.full].authenticated:
            self.routeStanza(el, fro, to)
            return
        self.sendError(el, "cancel", "service-unavailable")

    def getClient(self, jid):
        r = None
        jidStr = jid.full
        if jidStr == jid.bare:
            for cl in self.clients:
                if cl.startswith(jidStr + '/') and \
                   self.clients[cl].authenticated:
                    r = self.clients[cl]
        else:
            r = self.clients.get(jidStr, None)
        return r

    def routeStanza(self, el, fro, to):
        cl = self.getClient(fro)
        if not cl:
            return
        xml = utils.retag(el.xml, utils.COMPONENT_NS, utils.CLIENT_NS)
        xml.set('to', self.unquoteJID(to.full))
        # 'from' is removed so the guest server decides on the sender
        xml.attrib.pop('from', None)
        cl.send(utils.tostring(xml))

    # ---- presence routing ----

    def onPresence(self, el):
        fro = el['from']
        to = el['to']
        presenceType = el['type']
        try:
            fro = JID(fro)
            to = JID(to)
        except InvalidJID:
            return

        if to.full == self.cJid:
            if not self.shuttingDown:
                self.componentPresence(el, fro, presenceType)
            else:
                self.sendError(el, etype="cancel",
                               condition="service-unavailable")
            return

        cl = self.getClient(fro)
        if not cl:
            return
        uid = cl.uid

        if presenceType in ("available", "", None):
            if not fro.full in self.clients:
                return
            if not self.unquoteJID(to.bare) in cl.presences_available:
                cl.presences_available.append(self.unquoteJID(to.bare))
            if not self.unquoteJID(to.full) in cl.presences_available_full:
                cl.presences_available_full.append(self.unquoteJID(to.full))

        if presenceType == "subscribe":
            toUnq = self.unquoteJID(to.bare)
            if not self.db.getCount(
                    'rosters', "user_id=? AND jid=?",
                    (str(uid), toUnq)):
                self.db.execute(
                    "INSERT INTO rosters (user_id,jid) VALUES (?,?)", (str(uid), toUnq))
                self.db.commit()
            if toUnq in cl.guest_roster.items:
                subscription = cl.guest_roster.items[toUnq][1]
                if subscription in ("both", "to"):
                    p = self.make_presence(ptype="subscribed",
                                           pto=fro.bare, pfrom=to.bare)
                    p.send()
                    if subscription == "both":
                        p['type'] = "subscribe"
                        p.send()

                    for pr in list(cl.presences.keys()):
                        if pr.split('/')[0] == toUnq:
                            pres = cl.presences[pr]
                            xml = utils.retag(
                                pres.xml, utils.CLIENT_NS,
                                utils.COMPONENT_NS)
                            xml.set('from', self.quoteJID(pr))
                            xml.set('to', fro.full)
                            self.send(utils.tostring(xml))
                    return

        if presenceType in ("unsubscribe", "unsubscribed"):
            toUnq = self.unquoteJID(to.full)
            if self.db.getCount(
                    'rosters', "user_id=? AND jid=?",
                    (str(uid), toUnq)):
                self.db.execute(
                    "DELETE FROM rosters WHERE user_id=? AND jid=?", (str(uid), toUnq))
                self.db.commit()
                p = self.make_presence(ptype="unsubscribed",
                                       pto=fro.bare, pfrom=to.bare)
                p.send()
                if cl.remove_from_roster:
                    cl.guest_roster.removeItem(toUnq)
                else:
                    return

        self.routeStanza(el, fro, to)

    def componentPresence(self, el, fro, presenceType):
        uid = self.db.getIdByJid(fro.bare)
        if not uid:
            return
        if presenceType in ("available", "", None) and \
           self.db.isDisabled(uid):
            # Suspended account: refuse guest login but tell the user
            # how to get back in (ad-hoc Options works without one).
            lang = self.effectiveLang(self.db.getLangById(uid))
            self.debug.loginsLog(
                "User %s is trying to log in while suspended" %
                (fro.full))
            self.sendError(el, etype="cancel", condition="not-allowed")
            msg = self.make_message(mto=fro.bare, mfrom=self.cJid,
                                    mtype="chat")
            msg['body'] = i18n.t(lang, "msg_suspended")
            msg.send()
            return
        data = self.db.getDataById(uid)
        resource = fro.resource
        if resource:
            resource = "/" + resource
        else:
            resource = ""
        try:
            clientJid = JID(data[0] + "@" + data[2] + resource)
        except InvalidJID:
            self.sendError(el, etype="modify",
                           condition="not-acceptable")
            return
        if data[3] is None or data[3] == '':
            data[3] = data[2]
        newmd5 = hashlib.md5(
            ('%s@%s' % (data[0], data[2])).encode('utf-8')).hexdigest()
        if fro.full not in self.clients and \
           (presenceType in ("available", "", None)):
            self.debug.loginsLog(
                "User %s is trying to log in" % (fro.full))
            js = []
            history = None
            for element in list(el.xml):
                if utils.locname(element) == "x" and \
                   element.get("xmlns") == "j2j:history":
                    history = element
                    try:
                        hops = int(element.get("hops", 0))
                    except ValueError:
                        hops = 0
                    if hops > 3:
                        self.sendError(el, "cancel", "not-allowed")
                        return
                    element.set("hops", str(hops + 1))
                    for jidmd5 in list(element):
                        if utils.locname(jidmd5) == "jid":
                            js.append(jidmd5.text or '')
            if history is None:
                history = utils.addsub(el.xml, "x", "j2j:history")
                history.set("hops", "1")

            jhash = utils.addsub(history, "jid", "j2j:history")
            jhash.text = hashlib.md5(
                fro.bare.encode('utf-8')).hexdigest()
            jhash.set("gateway", self.cJid)
            js.append(hashlib.md5(fro.bare.encode('utf-8')).hexdigest())
            if newmd5 in js:
                self.sendError(el, "cancel", "conflict")
                self.debug.loginConflictLog(
                    "User %s has conflict login:\n%s" %
                    (fro.full, utils.tostring(el.xml)))
                return
            self.send_presence(
                ptype="unavailable", pto=fro.full, pfrom=self.cJid,
                pstatus=i18n.t(
                    self.effectiveLang(self.db.getLangById(uid)),
                    "status_logging_in"))
            self.clients[fro.full] = GuestClient(
                uid, el, self, fro, clientJid, data[3], data[1],
                data[4], data[5], data[6])
        elif fro.full in self.clients and presenceType == "unavailable":
            if self.clients[fro.full].connected:
                self.debug.loginsLog(
                    "User %s is trying to log out" % (fro.full))
                self.clients[fro.full].disconnect()
            else:
                self.clients[fro.full].need_disconnect = True
        elif fro.full in self.clients and \
             (presenceType in ("available", "", None)):
            if self.clients[fro.full].connected:
                xml = utils.retag(el.xml, utils.COMPONENT_NS,
                                  utils.CLIENT_NS)
                xml.attrib.pop("to", None)
                xml.attrib.pop("from", None)
                self.clients[fro.full].send(utils.tostring(xml))
        elif presenceType == "subscribe":
            self.send_presence(ptype="subscribed", pto=fro.full,
                               pfrom=self.cJid)

    def deleteClient(self, jid):
        if jid.full in self.clients:
            del self.clients[jid.full]

    def disconnectGuestSessions(self, bare_jid):
        """Drop every active guest session of *bare_jid* (used when an
        account gets suspended)."""
        for jid in list(self.clients.keys()):
            if jid == bare_jid or jid.startswith(bare_jid + "/"):
                cl = self.clients[jid]
                if cl.connected:
                    cl.disconnect()

    # ---- iq routing ----

    def onIq(self, el):
        fro = el['from']
        to = el['to']
        ID = el['id']
        iqType = el['type']
        try:
            fro = JID(fro)
            to = JID(to)
        except InvalidJID:
            return
        if to.full == self.cJid:
            return self.componentIq(el, fro, ID, iqType)
        if fro.full in self.clients and \
           self.clients[fro.full].authenticated:
            return self.routeStanza(el, fro, to)
        self.sendError(el, etype="cancel", condition="service-unavailable")

    def componentIq(self, el, fro, ID, iqType):
        for query in el.xml:
            xmlns = utils.nsname(query)
            node = query.get("node")
            if xmlns == utils.VCARD_NS and iqType == "result":
                self.result_vCard(el, fro, ID)
                return
            if xmlns == "jabber:iq:register" and iqType == "get":
                self.getRegister(el, fro, ID)
                return
            if xmlns == "jabber:iq:register" and iqType == "set":
                self.setRegister(el, fro, ID)
                return
            if xmlns == utils.DISCO_INFO_NS and iqType == "get":
                self.getDiscoInfo(el, fro, ID, node)
                return
            if xmlns == utils.DISCO_ITEMS_NS and iqType == "get":
                self.getDiscoItems(el, fro, ID, node)
                return
            if xmlns == "jabber:iq:last" and iqType == "get":
                self.getLast(fro, ID)
                return
            if xmlns == "jabber:iq:version" and iqType == "get":
                self.getVersion(fro, ID)
                return
            if xmlns == "jabber:iq:gateway" and iqType == "get":
                self.getIqGateway(fro, ID)
                return
            if xmlns == "jabber:iq:gateway" and iqType == "set":
                self.setIqGateway(el, fro, ID)
                return
            if xmlns == utils.VCARD_NS and iqType == "get" and \
               utils.locname(query) == "vCard":
                self.getvcard(fro, ID)
                return
            if xmlns == utils.COMMANDS_NS and \
               utils.locname(query) == "command" and iqType == "set":
                etype, condition = self.adhoc.onCommand(
                    el, fro, ID, node)
                if etype is not None:
                    self.sendError(el, etype=etype,
                                   condition=condition)
                return
            if xmlns == utils.STATS_NS:
                self.getStats(el, fro, ID)
                return
        self.sendError(el, etype="cancel",
                       condition="feature-not-implemented")

    def result_vCard(self, el, fro, ID):
        entry = self.adhoc.vCardSids.get(ID)
        if not entry:
            return
        if fro.bare != entry[0].bare:
            return
        if entry[0].full not in self.clients:
            return
        del self.adhoc.vCardSids[ID]
        xml = utils.retag(el.xml, utils.COMPONENT_NS, utils.CLIENT_NS)
        xml.attrib.pop("to", None)
        xml.attrib.pop("from", None)
        xml.set("type", "set")
        self.clients[entry[0].full].send(utils.tostring(xml))

    def getStats(self, el, fro, ID):
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", utils.STATS_NS)
        nodes = []
        for q in list(el.xml):
            if utils.locname(q) == "query":
                nodes = [c for c in list(q)
                         if utils.locname(c) == "stat"]
        if nodes:
            for node in nodes:
                if node.get("name") == "users/online":
                    o = utils.addsub(query, "stat", utils.STATS_NS)
                    o.set("name", "users/online")
                    o.set("units", "users")
                    o.set("value", str(len(self.clients)))
                if node.get("name") == "users/total":
                    t = utils.addsub(query, "stat", utils.STATS_NS)
                    t.set("name", "users/total")
                    t.set("units", "users")
                    t.set("value", str(self.db.getCount("users")))
        else:
            o = utils.addsub(query, "stat", utils.STATS_NS)
            o.set("name", "users/online")
            o.set("units", "users")
            o.set("value", str(len(self.clients)))
            t = utils.addsub(query, "stat", utils.STATS_NS)
            t.set("name", "users/total")
            t.set("units", "users")
            t.set("value", str(self.db.getCount("users")))
        self.send(utils.tostring(iq))

    def _newResultIq(self, fro, ID):
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("type", "result")
        iq.set("from", self.cJid)
        iq.set("to", fro.full)
        if ID:
            iq.set("id", ID)
        return iq

    def getvcard(self, fro, ID):
        iq = self._newResultIq(fro, ID)
        vcard = utils.addsub(iq, "vCard", utils.VCARD_NS)
        utils.addsub(vcard, "NICKNAME", utils.VCARD_NS,
                     text="J2J: Jabber-To-Jabber Transport")
        utils.addsub(vcard, "BDAY", utils.VCARD_NS, text="2026-08-21")
        utils.addsub(vcard, "DESC", utils.VCARD_NS,
                     text="Jabber-To-Jabber Transport")
        utils.addsub(vcard, "URL", utils.VCARD_NS,
                     text="https://jabberworld.info")
        self.send(utils.tostring(iq))

    def registerContext(self, fro):
        """(uid, data) describing the requester's registration state;
        *data* carries defaults for a fresh registration when uid is
        None."""
        uid = self.db.getIdByJid(fro.bare)
        if uid:
            return uid, self.db.getDataById(uid)
        return None, [None, None, None, None, 5222, False, False]

    def buildRegisterForm(self, parent, lang, uid, data):
        """Attach the jabber:x:data registration dialog to *parent*
        (either an iq:register <query/> or an ad-hoc <command/>)."""
        edit = uid is not None
        form = utils.createForm(parent, "form")
        utils.addTitle(form, i18n.t(lang, "reg_title"))
        if not edit:
            utils.addLabel(
                form, i18n.t(lang, "reg_new_instructions"))
        else:
            utils.addLabel(form, i18n.t(lang, "reg_edit_instructions"))
        jid_value = None
        if edit and data[0] and data[2]:
            jid_value = data[0] + "@" + data[2]
        utils.addTextBox(form, "jid", i18n.t(lang, "field_jid"),
                         jid_value, required=True)
        utils.addTextPrivate(form, "password",
                             i18n.t(lang, "field_password"),
                             data[1], required=True)
        utils.addTextBox(form, "domain", i18n.t(lang, "field_domain"),
                         data[3])
        utils.addTextBox(form, "port", i18n.t(lang, "field_port"),
                         str(data[4] if data[4] is not None else 5222))
        if not edit:
            utils.addCheckBox(form, "import_roster",
                              i18n.t(lang, "field_import_roster"),
                              data[5])
        utils.addListSingle(form, "language",
                            i18n.t(lang, "field_language"),
                            lang, i18n.options())
        return form

    def getRegister(self, el, fro, ID):
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", "jabber:iq:register")
        uid, data = self.registerContext(fro)
        lang = self.getUserLang(fro.bare)
        if uid is not None:
            utils.addsub(query, "registered", "jabber:iq:register")
        self.buildRegisterForm(query, lang, uid, data)
        self.send(utils.tostring(iq))

    def submitRegistration(self, el, fro):
        """Validate and apply a submitted registration x:data form
        (shared by jabber:iq:register and the ad-hoc "register"
        command). Returns (ok, error_condition, created); on success
        all side effects (DB writes, presences, notifications) have
        been performed."""
        jid_str = (utils.xdataValue(el, 'jid') or '').strip()
        if jid_str.count('@') < 1:
            return False, "jid-malformed", False
        username, server = jid_str.split('@', 1)
        try:
            JID(username + '@' + server)
        except InvalidJID:
            return False, "jid-malformed", False
        password = utils.xdataValue(el, 'password')
        if password == '':
            return False, "not-acceptable", False
        domain = utils.xdataValue(el, 'domain')
        if not domain:
            domain = server
        port = utils.xdataValue(el, 'port')
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = 5222
        import_roster = utils.strToBool(
            utils.xdataValue(el, 'import_roster'))
        lang_submitted = (utils.xdataValue(el, 'language') or '').strip()
        language = i18n.normalize(lang_submitted) if lang_submitted \
            else None
        uid = self.db.getIdByJid(fro.bare)
        edit = uid is not None
        if not edit:
            # remove_from_guest_roster defaults to 0 (schema default);
            # it is managed via the ad-hoc Options command.
            self.db.execute(
                "INSERT INTO users "
                "(jid,username,domain,server,password,port,"
                "import_roster) "
                "VALUES (?,?,?,?,?,?,?)",
                (fro.bare, username, domain, server, password,
                 port, int(import_roster)))
            uid = self.db.getIdByJid(fro.bare)
            self.db.execute(
                "INSERT INTO users_options (user_id,language) "
                "VALUES (?,?)", (str(uid), language))
            self.db.commit()
            pres = self.make_presence(ptype="subscribe",
                                      pto=fro.bare, pfrom=self.cJid)
            pres.send()
            if self.config.ADMINS and \
               self.config.REGISTRATION_NOTIFY:
                msg = self.make_message(
                    mto=self.cJid, mtype="chat", mfrom=self.cJid)
                msg['body'] = "J2J %s Registration notify:\n" \
                              "Host JID:%s\nGuest JID:%s" % (
                                  self.cJid, fro.full,
                                  username + "@" + server)
                for ajid in self.config.ADMINS:
                    msg['to'] = ajid
                    msg.send()
            self.debug.registrationsLog(
                "User %s is registered to guest-jid %s" %
                (fro.full, username + "@" + server))
            return True, None, True
        data = self.db.getDataById(uid)
        if data[0] != username or data[2] != server:
            a = self.db.fetchall(
                "SELECT jid FROM rosters WHERE user_id=?", (str(uid),))
            for unjid, in a:
                pres = self.make_presence(ptype="unsubscribe",
                                          pto=fro.bare,
                                          pfrom=self.quoteJID(unjid))
                pres.send()
                pres['type'] = 'unsubscribed'
                pres.send()
            self.db.execute(
                "DELETE FROM rosters WHERE user_id=?", (str(uid),))
        self.db.execute(
            "UPDATE users SET username=?,domain=?,server=?,"
            "password=?,port=? WHERE id=?",
            (username, domain, server, password, port, str(uid)))
        # Only touch the stored language when the form actually
        # carried the field (older cached forms may omit it).
        if lang_submitted:
            self.db.setLangById(uid, language)
        self.db.commit()
        self.debug.registrationsLog(
            "User %s has changed registration information "
            "to %s" % (fro.full, username + "@" + server))
        return True, None, False

    def setRegister(self, el, fro, ID):
        uid = self.db.getIdByJid(fro.bare)
        remove = False
        for q in list(el.xml):
            if utils.locname(q) == 'query':
                for child in list(q):
                    if utils.locname(child) == 'remove':
                        remove = True
        if remove:
            if uid is None:
                self.sendError(el, etype="auth",
                               condition="registration-required")
                return
            for j in list(self.clients.keys()):
                if j.startswith(fro.bare + "/") or j == fro.bare:
                    if self.clients[j].connected:
                        self.clients[j].disconnect()
            unPres = self.make_presence(ptype="unavailable",
                                        pto=fro.full)
            if fro.full in self.clients:
                for ojid in \
                        self.clients[fro.full].presences_available_full:
                    unPres['from'] = self.quoteJID(ojid)
                    unPres.send()
            ujids = self.db.fetchall(
                "SELECT jid FROM rosters WHERE user_id=?", (str(uid),))
            for ojid, in ujids:
                unPres['from'] = self.quoteJID(ojid)
                unPres['type'] = "unsubscribe"
                unPres.send()
                unPres['type'] = "unsubscribed"
                unPres.send()
            self.db.execute(
                "DELETE FROM rosters WHERE user_id=?", (str(uid),))
            self.db.execute(
                "DELETE FROM users_options WHERE user_id=?", (str(uid),))
            self.db.execute(
                "DELETE FROM users WHERE id=?", (str(uid),))
            self.db.commit()
            self.sendIqResult(fro.full, self.cJid, ID,
                              "jabber:iq:register")
            pres = self.make_presence(ptype="unsubscribe",
                                      pto=fro.full, pfrom=self.cJid)
            pres.send()
            pres['type'] = 'unsubscribed'
            pres.send()
            pres['type'] = 'unavailable'
            pres.send()
            self.debug.registrationsLog(
                "Client %s is unregistered" % fro.full)
            return
        ok, err, _created = self.submitRegistration(el, fro)
        if not ok:
            self.sendError(el, etype="modify", condition=err)
            return
        self.sendIqResult(fro.full, self.cJid, ID,
                          "jabber:iq:register")

    def getIqGateway(self, fro, ID):
        lang = self.getUserLang(fro.bare)
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", "jabber:iq:gateway")
        utils.addsub(query, "desc", "jabber:iq:gateway",
                     text=i18n.t(lang, "gw_desc"))
        utils.addsub(query, "prompt", "jabber:iq:gateway",
                     text=i18n.t(lang, "gw_prompt"))
        self.send(utils.tostring(iq))

    def setIqGateway(self, el, fro, ID):
        iq = self._newResultIq(fro, ID)
        prompt = ''
        for q in list(el.xml):
            if utils.locname(q) == 'query':
                for child in list(q):
                    if utils.locname(child) == 'prompt':
                        prompt = child.text or ''
        query = utils.addsub(iq, "query", "jabber:iq:gateway")
        utils.addsub(query, "jid", "jabber:iq:gateway",
                     text=self.quoteJID(prompt))
        self.send(utils.tostring(iq))

    def getLast(self, fro, ID):
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", "jabber:iq:last")
        query.set("seconds", str(int(time.time() - self.startTime)))
        self.send(utils.tostring(iq))

    def getVersion(self, fro, ID):
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", "jabber:iq:version")
        utils.addsub(query, "name", "jabber:iq:version",
                     text="J2J: Jabber-To-Jabber Transport")
        utils.addsub(query, "version", "jabber:iq:version",
                     text=self.VERSION)
        utils.addsub(query, "os", "jabber:iq:version",
                     text="Python %s, slixmpp %s" % (
                         platform.python_version(),
                         slixmpp.__version__))
        self.send(utils.tostring(iq))

    def getDiscoInfo(self, el, fro, ID, node):
        lang = self.getUserLang(fro.bare)
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", utils.DISCO_INFO_NS)
        if node:
            query.set("node", node)
            if node == 'http://jabber.org/protocol/commands':
                identity = utils.addsub(query, "identity",
                                        utils.DISCO_INFO_NS)
                identity.set("name", i18n.t(lang, "disco_commands"))
                identity.set("category", "automation")
                identity.set("type", "command-list")
            if node in self.adhoc.commands:
                if self.adhoc.commands[node][4] and \
                   fro.bare not in self.config.ADMINS:
                    self.sendError(el, etype="auth",
                                   condition="not-authorized")
                    return
                if self.adhoc.commands[node][3]:
                    uid = self.db.getIdByJid(fro.bare)
                    if not uid:
                        self.sendError(el, etype="auth",
                                       condition="not-authorized")
                        return
                identity = utils.addsub(query, "identity",
                                        utils.DISCO_INFO_NS)
                identity.set(
                    "name", i18n.t(lang, self.adhoc.commands[node][0]))
                identity.set("category", "automation")
                identity.set("type", "command-node")
                utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                             {"var": utils.COMMANDS_NS})
                utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                             {"var": "jabber:x:data"})
            if (node.startswith("groster") and
                    fro.full in self.clients) or \
               (node.startswith("users") and
                    fro.bare in self.config.ADMINS):
                utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                             {"var": utils.DISCO_ITEMS_NS})
                utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                             {"var": utils.DISCO_INFO_NS})
        else:
            identity = utils.addsub(query, "identity",
                                    utils.DISCO_INFO_NS)
            identity.set("name", "J2J: Jabber-To-Jabber Transport")
            identity.set("category", "gateway")
            identity.set("type", "XMPP")
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.VCARD_NS})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.COMMANDS_NS})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.STATS_NS})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.DISCO_ITEMS_NS})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.DISCO_INFO_NS})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": "jabber:iq:gateway"})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": "jabber:iq:register"})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": "jabber:iq:last"})
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": "jabber:iq:version"})
        self.send(utils.tostring(iq))

    def getDiscoItems(self, el, fro, ID, node):
        lang = self.getUserLang(fro.bare)
        iq = self._newResultIq(fro, ID)
        query = utils.addsub(iq, "query", utils.DISCO_ITEMS_NS)
        if node:
            query.set("node", node)
        if node is None:
            if fro.bare in self.config.ADMINS:
                utils.addDiscoItem(query, self.cJid,
                                   i18n.t(lang, "disco_users"),
                                   'users')
            if fro.full in self.clients:
                utils.addDiscoItem(
                    query, self.quoteJID(
                        self.clients[fro.full].client_jid.host),
                    i18n.t(lang, "disco_guest_server"))
                utils.addDiscoItem(
                    query, self.cJid,
                    i18n.t(lang, "disco_guest_roster"), "groster")
        elif node == "groster" and fro.full in self.clients:
            groups = self.clients[fro.full].guest_roster.getGroups()
            for group in groups:
                utils.addDiscoItem(query, self.cJid, group,
                                   "groster/" + group)
        elif node == "users" and fro.bare in self.config.ADMINS:
            utils.addDiscoItem(query, self.cJid,
                               i18n.t(lang, "disco_online_users"),
                               'users/online')
        elif node == "users/online" and \
                fro.bare in self.config.ADMINS:
            for user in self.clients:
                utils.addDiscoItem(query, user)
        elif node.startswith("groster/") and fro.full in self.clients:
            group = node[8:]
            contacts = self.clients[fro.full].guest_roster.getAllInGroup(group)
            for contact in contacts:
                utils.addDiscoItem(query, self.quoteJID(contact[0]),
                                   contact[1])
        elif node == "http://jabber.org/protocol/commands":
            self.adhoc.getCommandsList(query, lang, fro)
        elif node in self.adhoc.commands:
            if self.adhoc.commands[node][4] and \
               fro.bare not in self.config.ADMINS:
                self.sendError(el, etype="auth",
                               condition="not-authorized")
                return
            if self.adhoc.commands[node][3]:
                uid = self.db.getIdByJid(fro.bare)
                if not uid:
                    self.sendError(el, etype="auth",
                                   condition="not-authorized")
                    return
        self.send(utils.tostring(iq))

    def sendIqResult(self, to, fro, ID, xmlns):
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("type", "result")
        iq.set("to", to)
        iq.set("from", fro)
        if ID:
            iq.set("id", ID)
        self.send(utils.tostring(iq))

    def sendError(self, el, etype, condition, sender=None):
        node = el.xml if hasattr(el, 'xml') else el
        err = copy.deepcopy(node)
        src_from = node.get('from')
        src_to = node.get('to')
        if src_to is not None:
            err.set('from', src_to)
        if src_from is not None:
            err.set('to', src_from)
        err.set('type', 'error')
        error = utils.addsub(err, 'error', utils.COMPONENT_NS)
        error.set('type', etype)
        error.set('code', str(utils.errorCodeMap[condition]))
        utils.addsub(error, condition,
                     'urn:ietf:params:xml:ns:xmpp-stanzas')
        if sender is None:
            sender = self
        sender.send(utils.tostring(err))

    def sendProbes(self):
        jids = self.db.fetchall(
            'SELECT jid FROM users')
        for jid, in jids:
            self.send_presence(ptype='probe', pto=jid, pfrom=self.cJid)

    def requestShutdown(self, restart=False):
        """Runtime shutdown (ad-hoc admin command); optionally re-exec
        the whole process afterwards to restart the transport."""
        self.restartRequested = restart
        self.debug.logger.info("%s requested via ad-hoc command",
                               "Restart" if restart else "Stop")
        self.shutdownHandler()

    def shutdownHandler(self, signum=None, frame=None):
        if self.shuttingDown:
            self.loop.stop()
            return
        self.shuttingDown = True
        presence = self.make_presence(ptype='unavailable', pto=self.cJid)
        for cl in list(self.clients.values()):
            presence['from'] = cl.host_jid.full
            self.componentPresence(presence, cl.host_jid, 'unavailable')
        self.disconnect(wait=1)
        self.loop.call_later(3, self.loop.stop)

    # ---- JID quoting ----

    def quoteJID(self, ujid):
        return utils.quoteJID(ujid, self.cJid)

    def unquoteJID(self, qjid):
        return utils.unquoteJID(qjid, self.cJid)
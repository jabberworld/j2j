# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the J2J gateway component.

import copy
import asyncio
import hashlib
import platform
import time
import uuid

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
from dialogs import MessageDialogs

TRANSPORT_PHOTO = (
    "iVBORw0KGgoAAAANSUhEUgAAABYAAAAgCAYAAAAWl4iLAAAFbUlEQVR42q2WA3hbbRuAT63Ztm3W9lS3V93OLv78X23O3mpztq04Jynj1Ek1b+l5vjOj/Hb1jnOecz+v3xf5DgDINKSnT6vLyEhgamgcqIyJKefExmKc6Ghg2Njk08aMOVDp4nKg4eJFX2Fg4Hh4904e6YrmzExZyc2bphVeXkkse3spEc/R3YtpZQVsH5+CqiNHFnQqrj9ypH/F5s0YUVn5x43kSZOAoqHxOYmIOmZMFX369CrywIFVVD09KWXWrK9xeDzd3LyNt3dvCM/LS6admOvk1J+ppfVVOHEiVpOdXcfz8bFsvHRJ9xGCKDGmT1dmLVmiTNfRUWl59EhHQCCY1ubmUlANjdfEfv2APGqUtExHJ4Lr4vK7nLN2bX90+XKgzJmDiWJiwlsfPlRGuuE9i6Ugyc8fW+nuHkyeNQsjjxnzie/rGwAAP+XVYWF9Kzw9W8vXr98vCg+XRf4jNcePE2iamkA3NPzA2b170m8XW2/enIz8JdDUJFN16FAw3gdSbkQE+h5F+yK9RX16unKlry+TMmECJr5wwRbpTari4qzIs2dLWebmCVBdLdNrYt6ePaqojk4N08AAq8vKGtlr4ncMhjL/8GHOSwSB2jNnCEhvUrJqlR8JH9ssR8f9vSoW+vj4k6dMAR6+vrQfPrXn5YCXmwAkt8vAjHQDAFWoTVMCmvdyKPu/QpcdGBjoT5kxAzgEQgdifu4MuLH0EzwwCoRHFneh6ko4vNz9Em4uxIDomtdpG5PJsmXOzvEkZWXgnzhR04E4qRhu6LTBW74+kLyy4YENBk/tRcAIaYUrA9DOxOLCwsEsK6s6Iq7g+fsHdCA+cw5u6LXB+yp9EF48CCVHb0F5rBqU7SfCnQUdipsLCmQqN23aSx47FpimptBQWDixgylKPwg3tDFouGX14z/20clwW+M18HIu/RmPSSQy4qIiV3y9kJIUFTF+aGgEtLbKthcXIYrwwqcGJPe1EByoOqoKj4wK4fnWVqi6PqRdExQXu7OcnYGoogK82Fhhy8OHA5DOgI810398F14NhdvL3gI/w+zPOHypdEetrDCikhKU79hR1XThwqzfAj4JBIoN2dnqIh+foe2SCHL1gOZr+Vub5uUNEB47dp4yfPhHkpoaVurhcb/p4sUZ7ef5jh0jWBYWH9ElSzgcF5dhSBe8un9flePn95g0YgRQ1dXbhNHRKext2+Q6HirJyYPLvb1riYqKgG+qPFFQ0JDOxOzt223JkycDy9q6RRgVtazl7l1c2gVsB4epJTY2VaQhQ4Cpq1tWYmi4uv7oUfWGkyfV+du2qbNtbBY337vXh7V2LYeurt5cHRu7DOkOUUiIu2D//rstN29qCxMSitC1a8W0adOAZmgIdGNjYKxaBZyQkEZ8Eqyi6esDl0CI7dkiffiwEx2X4NXj1qakbGvOzZ3IDgjQFV+9erYuP/8oc8WKpW9evJhbpqs7mzZnDuC78iKkp1SfOEFA7e3h87mhwtubxU9M9MM3WuPG7Gxj/OxhUhUQoMmcP382Y+lSEGzevKRHUvGVKzt4AQFldWlpOmV2dndoy5d//NzrlLlzgbpyJVAWLwZ03br3wshIc/q8eVBubNwzMXXmzP99HuTCkydrmq5fH1ebkTG+8fLlC2wXl0d4KR+xnZ0f1Z88mV936tQ8hqkpRp04sWfiMgODMejKlWzy6NFQ6uBQLzp82K/p6lVNfJuRK8FfbysqZrE9PIxfo6iO5Pz5JLwTpyI9pSEra4IgJia3xNNTSh42DGgWFlI8GZOlrc2kW1o2UfHmwKWnkL8BAGTwo9PMhkuX/qmwt0+iDB2ahK+vSfT585Pw/xIbUlPle+r6F/yJD5mkmSgpAAAAAElFTkSuQmCC")

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
        self.dialogs = MessageDialogs(self)
        # Full guest JIDs whose available presence was actually forwarded
        # to the host account, keyed by uid. This is the authoritative set
        # of (contact, resource) pairs to take offline on disconnect: it
        # lives on the component, so it survives guest stream teardown and
        # GuestClient reconnection for as long as the process runs.
        self.presence_resources = {}
        self.shuttingDown = False
        self.restartRequested = False
        self.startTime = 0
        # Pending disco#info probes (iq id -> callback) and the
        # per-resource XEP-0144 support cache built from them.
        self.pending_disco = {}
        self.rosterx_support = {}
        # Pending vCard fetches for virtual JIDs (transport users and
        # guest-roster contacts): iq id -> (requester full jid, original
        # request id, deep copy of the original request stanza).
        self.pending_vcards = {}
        # IQs sent directly by the component on behalf of an administrator
        # to a virtual JID: internal id -> original request metadata.
        self.pending_virtual_iq = {}
        # Liveness watchdog for the component link: slixmpp no longer
        # reconnects on its own and a half-open TCP connection (NAT
        # timeout, crashed host) produces neither EOF nor error.
        self.reconnectAttempts = 0
        self.lastRecvData = 0.0
        self.selfPingIds = set()
        self._selfPingTimer = None
        self._livenessTimer = None
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
        self.add_event_handler('disconnected', self.componentDisconnected)
        self.add_event_handler('connection_failed',
                               self.componentConnectFailed)
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
        self.reconnectAttempts = 0
        self.startTime = time.time()
        if self.config.SEND_PROBES:
            for jid in self.db.activeUserJids():
                self.send_presence(ptype='probe', pto=jid,
                                   pfrom=self.cJid)
        sock = None
        if self.transport is not None:
            sock = self.transport.get_extra_info('socket')
        if sock is not None:
            utils.enableTcpKeepalive(sock)
        # Liveness watchdog: fresh baseline and periodic probes.
        self.lastRecvData = time.monotonic()
        self._scheduleSelfPing()
        self._scheduleLivenessCheck()
        self.debug.logger.info("Connected to server, service available at %s",
                               self.cJid)

    def componentDisconnected(self, event=None):
        self._cancelLivenessTimers()
        if self.shuttingDown:
            return
        self.reconnectAttempts += 1
        delay = min(5 * self.reconnectAttempts, 60)
        self.debug.logger.warning(
            "Connection to server lost (%s); reconnecting in %ds",
            event or "unknown reason", delay)
        self.loop.call_later(delay, self.connect)

    def componentConnectFailed(self, event=None):
        if not self.shuttingDown:
            self.debug.logger.warning(
                "Connection attempt to server failed: %s", event)

    # ---- link liveness ----

    def data_received(self, data):
        if data:
            self.lastRecvData = time.monotonic()
        ComponentXMPP.data_received(self, data)

    def _cancelLivenessTimers(self):
        for handle in (self._selfPingTimer, self._livenessTimer):
            if handle is not None:
                try:
                    handle.cancel()
                except Exception:
                    pass
        self._selfPingTimer = None
        self._livenessTimer = None

    def _scheduleSelfPing(self):
        if self.shuttingDown:
            return
        self._selfPingTimer = self.loop.call_later(
            60, self.sendSelfPing)

    def sendSelfPing(self):
        """Ping the transport's own JID: the server routes the probe
        back to us, so a reply proves the link works in both
        directions (an unanswered probe leaves lastRecvData stale)."""
        if self.transport is None or self.shuttingDown:
            return
        pid = uuid.uuid4().hex
        self.selfPingIds.add(pid)
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("type", "get")
        iq.set("from", self.cJid)
        iq.set("to", str(JID(self.cJid).bare))
        iq.set("id", pid)
        utils.addsub(iq, "ping", "urn:xmpp:ping")
        try:
            self.send(utils.tostring(iq))
        except Exception:
            pass
        # Keep the set bounded even if replies never arrive.
        while len(self.selfPingIds) > 8:
            self.selfPingIds.pop()
        self._scheduleSelfPing()

    def _scheduleLivenessCheck(self):
        if self.shuttingDown:
            return
        self._livenessTimer = self.loop.call_later(
            30, self.livenessCheck)

    def livenessCheck(self):
        if self.transport is None or self.shuttingDown:
            return
        silent = time.monotonic() - self.lastRecvData
        if silent > 150:
            # Nothing at all came back (not even our own pings being
            # routed): the connection is a black hole. Force it closed;
            # componentDisconnected schedules the reconnect.
            self.debug.logger.warning(
                "No data from the server for %.0fs; "
                "forcing reconnect", silent)
            self.abort()
            return
        self._scheduleLivenessCheck()

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
        try:
            fro = JID(el['from'])
            to = JID(el['to'])
        except InvalidJID:
            return
        if self._isToComponent(to):
            body = el['body']
            if body:
                self.dialogs.handle(fro, body)
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
        real_to = self.unquoteJID(to.full)
        try:
            JID(real_to)
        except InvalidJID:
            self.debug.logger.debug(
                "Dropping stanza to unquotable %r: %r", to.full, real_to)
            if el.name == 'iq':
                self.sendError(el, "cancel", "jid-malformed")
            return
        xml = utils.retag(el.xml, utils.COMPONENT_NS, utils.CLIENT_NS)
        xml.set('to', real_to)
        # 'from' is removed so the guest server decides on the sender
        xml.attrib.pop('from', None)
        if el.name == 'message':
            uid = self.db.getIdByJid(fro.bare)
            if uid:
                opts = self.db.getOptsById(uid)
                if opts is not None and not utils.strip_relay_features(
                        xml, bool(opts[7]), bool(opts[8]), bool(opts[9])):
                    return
        cl.send(utils.tostring(xml))

    # ---- presence routing ----

    def onPresence(self, el):
        try:
            fro = JID(el['from'])
            to = JID(el['to'])
            presenceType = el['type']
        except InvalidJID:
            return

        if self._isToComponent(to):
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
            # Record only contacts that actually exist on the guest
            # account; otherwise db.rosters would accumulate entries for
            # subscriptions the guest never confirmed. Contacts added
            # through the guest roster are recorded by onRosterResult.
            if toUnq in cl.guest_roster.items and not self.db.getCount(
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
            self.connectGuestSession(fro, uid, el)
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

    def connectGuestSession(self, fro, uid, el):
        """(Re)establish a guest session for *uid* using stored
        credentials. *fro* is the host JID (used as the session key and
        the remote resource); *el* is the presence stanza replayed to
        the remote server on session start. Shared by the inbound
        available-presence path and the ad-hoc Options re-enable path."""
        if fro.full in self.clients:
            return
        lang = self.effectiveLang(self.db.getLangById(uid))
        self.send_presence(
            ptype="unavailable", pto=fro.full, pfrom=self.cJid,
            pstatus=i18n.t(lang, "status_logging_in"))
        data = self.db.getDataById(uid)
        if not data:
            return
        resource = fro.resource or ""
        try:
            clientJid = JID(data[0] + "@" + data[2] +
                           ("/" + resource if resource else ""))
        except InvalidJID:
            self.sendError(el, etype="modify",
                           condition="not-acceptable")
            return
        if data[3] is None or data[3] == '':
            data[3] = data[2]
        self.clients[fro.full] = GuestClient(
            uid, el, self, fro, clientJid, data[3], data[1],
            data[4], data[5], data[6], data[7])

    # ---- iq routing ----

    def _isToComponent(self, to):
        """True when *to* addresses the component itself.

        Compares normalized bare JIDs so a resource or a case/whitespace
        difference between the configured JID and the address actually
        delivered by the server cannot route component IQs to a guest
        client by mistake.
        """
        return str(to.bare).lower() == str(JID(self.cJid).bare).lower()

    def onIq(self, el):
        ID = el['id']
        iqType = el['type']
        try:
            fro = JID(el['from'])
            to = JID(el['to'])
        except InvalidJID:
            return
        self.debug.logger.debug(
            "onIq: to=%r cJid=%r fro=%r type=%s",
            to.full, self.cJid, fro.full, iqType)
        if self._isToComponent(to):
            return self.componentIq(el, fro, to, ID, iqType)
        if fro.bare in self.config.ADMINS and iqType == "get" and \
                self._proxyAdminVirtualIq(el, fro, to, ID):
            return
        if fro.full in self.clients and \
           self.clients[fro.full].authenticated:
            return self.routeStanza(el, fro, to)
        self.sendError(el, etype="cancel", condition="service-unavailable")

    def componentIq(self, el, fro, to, ID, iqType):
        # Replies to our own liveness probes: consume silently.
        if iqType == "result" and ID in self.selfPingIds:
            self.selfPingIds.discard(ID)
            return
        if ID in self.pending_virtual_iq and iqType in ("result", "error"):
            self.resultVirtualIq(el, fro, ID)
            return
        # Replies to our disco#info probes are matched by id: error
        # replies may not carry a disco-namespaced child at all.
        if ID in self.pending_disco and iqType in ("result", "error"):
            self.resultDiscoInfo(el, fro, ID)
            return
        if ID in self.pending_vcards and iqType in ("result", "error"):
            self.resultVirtualVcard(el, fro, ID, iqType == "result")
            return
        for query in el.xml:
            xmlns = utils.nsname(query)
            node = query.get("node")
            if xmlns == utils.VCARD_NS and iqType in ("result", "error"):
                self.result_vCard(el, fro, ID, iqType == "result")
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
            if xmlns == "urn:xmpp:ping" and iqType == "get":
                # XEP-0199 responder: also guarantees the liveness
                # self-ping produces incoming traffic.
                self.send(utils.tostring(self._newResultIq(fro, ID)))
                return
            if xmlns == "jabber:iq:version" and iqType == "get":
                self.getVersion(fro, ID)
                return
            if xmlns == "jabber:iq:gateway" and iqType == "get":
                try:
                    self.getIqGateway(fro, ID)
                except Exception:
                    self.debug.logger.exception("getIqGateway failed")
                    self.sendError(el, etype="cancel",
                                   condition="internal-server-error")
                return
            if xmlns == "jabber:iq:gateway" and iqType == "set":
                try:
                    self.setIqGateway(el, fro, ID)
                except Exception:
                    self.debug.logger.exception("setIqGateway failed")
                    self.sendError(el, etype="cancel",
                                   condition="internal-server-error")
                return
            if xmlns == utils.VCARD_NS and iqType == "get" and \
               utils.locname(query) == "vCard":
                self.getvcard(el, fro, ID, to)
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

    def _proxyAdminVirtualIq(self, el, fro, to, ID):
        """Proxy admin disco/vCard requests directly from the component.

        The guest account used for normal virtual-JID routing may not be
        subscribed to transport users. Component-originated requests avoid
        that guest-roster authorization check.
        """
        query = None
        namespace = None
        for child in el.xml:
            namespace = utils.nsname(child)
            if namespace in (utils.DISCO_INFO_NS, utils.VCARD_NS):
                query = child
                break
        if query is None:
            return False
        try:
            real = str(self.unquoteJID(to.full))
        except Exception:
            return False
        if not real or '@' not in real:
            return False

        proxy_id = uuid.uuid4().hex
        request = utils.addsub(None, "iq", utils.COMPONENT_NS)
        request.set("type", "get")
        request.set("to", real)
        request.set("from", self.cJid)
        request.set("id", proxy_id)
        request.append(copy.deepcopy(query))
        self.pending_virtual_iq[proxy_id] = (
            str(fro.full), str(ID), copy.deepcopy(el.xml), str(to.full),
            namespace)

        def on_timeout():
            entry = self.pending_virtual_iq.pop(proxy_id, None)
            if entry is not None:
                self.debug.logger.debug(
                    "virtual IQ fetch for %s timed out" % real)
                self.sendError(entry[2], etype="cancel",
                               condition="remote-server-not-found")

        try:
            self.loop.call_later(6, on_timeout)
        except (AttributeError, RuntimeError):
            on_timeout()
        self.send(utils.tostring(request))
        return True

    def resultVirtualIq(self, el, fro, proxy_id):
        """Return a direct component proxy result under its virtual JID."""
        entry = self.pending_virtual_iq.pop(proxy_id, None)
        if entry is None:
            return
        requester, original_id, original_xml, virtual_jid, namespace = entry
        result = utils.addsub(None, "iq", utils.COMPONENT_NS)
        result.set("type", el['type'])
        result.set("from", virtual_jid)
        result.set("to", requester)
        if original_id:
            result.set("id", original_id)
        if el['type'] == "result":
            for child in el.xml:
                result.append(copy.deepcopy(child))
            if namespace == utils.DISCO_INFO_NS:
                query = next((child for child in result
                              if utils.nsname(child) == utils.DISCO_INFO_NS),
                             None)
                if query is not None and not any(
                        child.get('var') == utils.VCARD_NS
                        for child in query
                        if utils.locname(child) == 'feature'):
                    utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                                 {"var": utils.VCARD_NS})
        else:
            for child in el.xml:
                result.append(copy.deepcopy(child))
        self.send(utils.tostring(result))

    def result_vCard(self, el, fro, ID, success=True):
        if self.dialogs.result_vcard(el, fro, ID, success):
            return
        entry = self.adhoc.vCardSids.get(ID)
        if not entry:
            return
        if fro.bare != entry[0].bare:
            return
        if entry[0].full not in self.clients:
            return
        del self.adhoc.vCardSids[ID]
        if success:
            xml = utils.retag(el.xml, utils.COMPONENT_NS, utils.CLIENT_NS)
            xml.attrib.pop("to", None)
            xml.attrib.pop("from", None)
            xml.set("type", "set")
            self.clients[entry[0].full].send(utils.tostring(xml))
        self.adhoc.finishReplica(entry[0], entry[1], ID, success)

    # ---- XEP-0144 support probing ----

    def probeRosterxSupport(self, full_jid, callback):
        """Ask *full_jid* for disco#info and invoke
        callback(supported) telling whether it announces the
        'http://jabber.org/protocol/rosterx' feature (XEP-0144).
        Results are cached per full JID; an error reply or a timeout
        counts as unsupported."""
        supported = self.rosterx_support.get(full_jid)
        if supported is not None:
            callback(supported)
            return
        iq_id = uuid.uuid4().hex
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("type", "get")
        iq.set("to", str(full_jid))
        iq.set("from", self.cJid)
        iq.set("id", iq_id)
        utils.addsub(iq, "query", utils.DISCO_INFO_NS)
        self.pending_disco[iq_id] = callback

        def on_timeout():
            cb = self.pending_disco.pop(iq_id, None)
            if cb is not None:
                self.debug.logger.debug(
                    "disco#info probe to %s timed out" % full_jid)
                self.rosterx_support[str(full_jid)] = False
                cb(False)

        try:
            self.loop.call_later(3, on_timeout)
        except (AttributeError, RuntimeError):
            on_timeout()
        self.send(utils.tostring(iq))

    def resultDiscoInfo(self, el, fro, ID):
        cb = self.pending_disco.pop(ID, None)
        if cb is None:
            return
        supported = False
        for feature in el.xml.iter():
            if feature.get("var") == "http://jabber.org/protocol/rosterx":
                supported = True
                break
        self.rosterx_support[str(fro)] = supported
        cb(supported)

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

    def getvcard(self, el, fro, ID, to):
        """Serve a vCard-temp result. For the transport's own JID the
        static service card is returned; for a virtual JID (a transport
        user or a guest-roster contact) the real entity's card is fetched
        from its home server asynchronously."""
        if self._isToComponent(to):
            iq = self._newResultIq(fro, ID)
            vcard = utils.addsub(iq, "vCard", utils.VCARD_NS)
            utils.addsub(vcard, "NICKNAME", utils.VCARD_NS,
                         text="J2J: Jabber-To-Jabber Transport")
            utils.addsub(vcard, "BDAY", utils.VCARD_NS, text="2026-08-21")
            utils.addsub(vcard, "DESC", utils.VCARD_NS,
                         text="Jabber-To-Jabber Transport")
            utils.addsub(vcard, "URL", utils.VCARD_NS,
                         text="https://jabberworld.info")
            photo = utils.addsub(vcard, "PHOTO", utils.VCARD_NS)
            utils.addsub(photo, "TYPE", utils.VCARD_NS,
                         text="image/png")
            utils.addsub(photo, "BINVAL", utils.VCARD_NS,
                         text=TRANSPORT_PHOTO)
            self.send(utils.tostring(iq))
            return
        # Virtual JID: only connected host clients and admins may use the
        # transport as a vCard proxy.
        if fro.full not in self.clients and \
           fro.bare not in self.config.ADMINS:
            self.sendError(el, etype="auth", condition="not-authorized")
            return
        try:
            real = str(self.unquoteJID(to.full))
        except Exception:
            real = None
        if not real or '@' not in real:
            self.sendError(el, etype="cancel", condition="item-not-found")
            return
        fetch_id = uuid.uuid4().hex
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("type", "get")
        iq.set("to", real)
        iq.set("from", self.cJid)
        iq.set("id", fetch_id)
        utils.addsub(iq, "vCard", utils.VCARD_NS)
        self.pending_vcards[fetch_id] = (fro.full, ID,
                                         copy.deepcopy(el.xml))

        def on_timeout():
            entry = self.pending_vcards.pop(fetch_id, None)
            if entry is not None:
                self.debug.logger.debug(
                    "vCard fetch for %s timed out" % real)
                self.sendError(entry[2], etype="cancel",
                               condition="remote-server-not-found")

        try:
            self.loop.call_later(6, on_timeout)
        except (AttributeError, RuntimeError):
            on_timeout()
        self.send(utils.tostring(iq))

    def resultVirtualVcard(self, el, fro, ID, success):
        """Relay a fetched vCard back to whoever asked for it under a
        virtual JID."""
        entry = self.pending_vcards.pop(ID, None)
        if entry is None:
            return
        requester_full, orig_id, orig_el = entry
        if not success:
            self.sendError(orig_el, etype="cancel",
                           condition="item-not-found")
            return
        vcard = None
        for child in el.xml:
            if utils.locname(child) == "vCard":
                vcard = child
                break
        if vcard is None:
            self.sendError(orig_el, etype="cancel",
                           condition="item-not-found")
            return
        iq = self._newResultIq(JID(requester_full), orig_id)
        iq.append(copy.deepcopy(vcard))
        self.send(utils.tostring(iq))

    def registerContext(self, fro):
        """(uid, data) describing the requester's registration state;
        *data* carries defaults for a fresh registration when uid is
        None."""
        uid = self.db.getIdByJid(fro.bare)
        if uid:
            return uid, self.db.getDataById(uid)
        return None, [None, None, None, None, 5222, False, False, None]

    @staticmethod
    def defaultImportMode(config, rosterx_supported):
        """Registration-form preselection: an explicit [general]
        import_mode wins; "auto" offers XEP-0144 roster item exchange
        when the client announces support and otherwise offers no
        import."""
        if config.IMPORT_MODE == "auto":
            return 2 if rosterx_supported else 0
        return {"off": 0, "subscribe": 1, "rosterx": 2}[config.IMPORT_MODE]

    def buildRegisterForm(self, parent, lang, uid, data,
                          mode_default=None):
        """Attach the jabber:x:data registration dialog to *parent*
        (either an iq:register <query/> or an ad-hoc <command/>).
        *mode_default* preselects the roster import mechanism for a
        fresh registration (edit forms preselect the stored value)."""
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
        modes = [("0", i18n.t(lang, "import_opt_off")),
                 ("1", i18n.t(lang, "import_opt_subscribe")),
                 ("2", i18n.t(lang, "import_opt_rosterx"))]
        mode = data[5] if edit else mode_default
        utils.addListSingle(form, "import_roster",
                            i18n.t(lang, "field_import_mode"),
                            str(mode if mode in (0, 1, 2) else 0),
                            modes)
        group = self.config.ROSTER_GROUP_NAME
        if edit and data[7]:
            group = data[7]
        utils.addTextBox(form, "import_group",
                         i18n.t(lang, "field_import_group"), group)
        utils.addListSingle(form, "language",
                            i18n.t(lang, "field_language"),
                            lang, i18n.options())
        return form

    def getRegister(self, el, fro, ID):
        uid, data = self.registerContext(fro)
        lang = self.getUserLang(fro.bare)

        def send_form(rosterx_supported):
            iq = self._newResultIq(fro, ID)
            query = utils.addsub(iq, "query", "jabber:iq:register")
            if uid is not None:
                utils.addsub(query, "registered", "jabber:iq:register")
            mode_default = self.defaultImportMode(self.config,
                                                  rosterx_supported)
            self.buildRegisterForm(query, lang, uid, data,
                                   mode_default=mode_default)
            self.send(utils.tostring(iq))

        if uid is not None:
            # Editing an existing registration: no probe needed, the
            # stored mechanism is preselected.
            send_form(False)
        else:
            self.probeRosterxSupport(fro.full, send_form)

    def submitRegistration(self, el, fro):
        """Validate and apply a submitted registration x:data form
        (shared by jabber:iq:register and the ad-hoc "register"
        command). Returns (ok, error_condition, created); on success
        all side effects (DB writes, presences, notifications) have
        been performed."""
        jid_str = (utils.xdataValue(el, 'jid') or '').strip()
        if jid_str.count('@') != 1:
            return False, "jid-malformed", False
        username, server = jid_str.split('@', 1)
        try:
            parsed = JID(username + '@' + server)
            if parsed.resource or not parsed.user or not parsed.server:
                raise InvalidJID
        except InvalidJID:
            return False, "jid-malformed", False
        password = utils.xdataValue(el, 'password')
        if not password or len(password) > 256:
            return False, "not-acceptable", False
        domain = utils.xdataValue(el, 'domain')
        if not domain:
            domain = server
        if any(ch.isspace() for ch in domain):
            return False, "not-acceptable", False
        try:
            JID("user@" + domain)
        except InvalidJID:
            return False, "not-acceptable", False
        port = utils.xdataValue(el, 'port')
        try:
            port = int(port)
        except (ValueError, TypeError):
            return False, "not-acceptable", False
        if not 1 <= port <= 65535:
            return False, "not-acceptable", False
        import_roster = (utils.xdataValue(el, 'import_roster') or
                         '').strip()
        if import_roster == '2':
            import_roster = 2
        elif import_roster in ('1', 'true'):
            import_roster = 1
        elif import_roster in ('', '0', 'false'):
            import_roster = 0
        else:
            return False, "not-acceptable", False
        import_group = (utils.xdataValue(el, 'import_group') or
                        '').strip()[:128] or None
        lang_submitted = (utils.xdataValue(el, 'language') or '').strip()
        language = i18n.normalize(lang_submitted) if lang_submitted else None
        if lang_submitted and language != lang_submitted.lower():
            return False, "not-acceptable", False
        uid = self.db.getIdByJid(fro.bare)
        edit = uid is not None
        if not edit:
            # remove_from_guest_roster defaults to 0 (schema default);
            # it is managed via the ad-hoc Options command.
            self.db.execute(
                "INSERT INTO users "
                "(jid,username,domain,server,password,port,"
                "import_roster,import_group) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (fro.bare, username, domain, server,
                 self.db.encryptPassword(password),
                 port, int(import_roster), import_group))
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
            (username, domain, server,
             self.db.encryptPassword(password), port, str(uid)))
        # Only touch import mechanism/group/language when the form
        # actually carried the fields (older cached forms may omit
        # them).
        mode_submitted = utils.xdataValue(el, 'import_roster')
        if mode_submitted is not None:
            self.db.execute(
                "UPDATE users SET import_roster=?,import_group=? "
                "WHERE id=?",
                (int(import_roster), import_group, str(uid)))
        if lang_submitted:
            self.db.setLangById(uid, language)
        self.db.commit()
        self.debug.registrationsLog(
            "User %s has changed registration information "
            "to %s" % (fro.full, username + "@" + server))
        return True, None, False

    def deleteAccount(self, fro):
        """Tear down *fro*'s transport account: disconnect the guest
        session(s), take every virtual contact (and the transport itself)
        offline and remove them from the user's roster, drop all DB rows,
        and signal the user's client that the transport went unavailable.
        Shared by the jabber:iq:register 'remove' flow and the ad-hoc
        'Delete account' command."""
        uid = self.db.getIdByJid(fro.bare)
        sessions = [cl for j, cl in list(self.clients.items())
                    if j.startswith(fro.bare + "/") or j == fro.bare]
        if uid:
            if sessions:
                for cl in sessions:
                    self.offlineUser(uid, cl.host_jid,
                                     client=cl, remove=True)
            else:
                self.offlineUser(uid, fro, remove=True)
        for cl in sessions:
            if cl.connected:
                cl.disconnect()
        if uid:
            self.db.execute(
                "DELETE FROM rosters WHERE user_id=?", (str(uid),))
            self.db.execute(
                "DELETE FROM users_options WHERE user_id=?", (str(uid),))
            self.db.execute(
                "DELETE FROM users WHERE id=?", (str(uid),))
            self.db.commit()
        self.debug.registrationsLog(
            "Client %s is unregistered" % fro.full)

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
            self.deleteAccount(fro)
            self.sendIqResult(fro.full, self.cJid, ID,
                              "jabber:iq:register")
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
            # Informational: the transport mirrors <sent> carbons of
            # messages written from other clients of the guest account.
            utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                         {"var": utils.CARBONS_NS})
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
            cl = self.clients[fro.full]
            # The guest account itself must never show up as a roster
            # contact in the service browser.
            groups = cl.guest_roster.getGroups(
                i18n.t(lang, "disco_ungrouped"),
                exclude={str(cl.client_jid.bare)})
            for group in groups:
                utils.addDiscoItem(query, self.cJid, group,
                                   "groster/" + group)
        elif node == "users" and fro.bare in self.config.ADMINS:
            utils.addDiscoItem(query, self.cJid,
                               i18n.t(lang, "disco_online_users"),
                               'users/online')
            utils.addDiscoItem(query, self.cJid,
                               i18n.t(lang, "disco_all_users"),
                               'users/all')
        elif node == "users/online" and \
                fro.bare in self.config.ADMINS:
            for cl in self.clients.values():
                utils.addDiscoItem(query,
                                   self.quoteJID(cl.host_jid.bare),
                                   str(cl.host_jid.bare))
        elif node == "users/all" and \
                fro.bare in self.config.ADMINS:
            for (jid,) in self.db.fetchall("SELECT jid FROM users"):
                utils.addDiscoItem(query, self.quoteJID(jid), jid)
        elif node.startswith("groster/") and fro.full in self.clients:
            cl = self.clients[fro.full]
            group = node[8:]
            contacts = cl.guest_roster.getAllInGroup(
                group, i18n.t(lang, "disco_ungrouped"),
                exclude={str(cl.client_jid.bare)})
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

    # ---- forwarded presence bookkeeping ----

    def notePresenceForwarded(self, uid, full_jid):
        """Record that *full_jid* (a guest-side contact resource) was
        made available to the host account and therefore needs an
        unavailable presence on disconnect."""
        self.presence_resources.setdefault(uid, set()).add(str(full_jid))

    def notePresenceWithdrawn(self, uid, full_jid):
        """Forget *full_jid*: its unavailable presence was forwarded, so
        there is nothing left to clear on disconnect."""
        known = self.presence_resources.get(uid)
        if known:
            known.discard(str(full_jid))

    def drainPresenceResources(self, uid):
        """Return (and clear) every recorded full JID for *uid*."""
        return self.presence_resources.pop(uid, set())

    def offlineUser(self, uid, host_jid, client=None, remove=False):
        """While the component stream is still up, mark every virtual
        contact of *uid* (plus the transport service JID itself) as
        unavailable to *host_jid*. When *remove* is true, also send
        unsubscribe/unsubscribed so the contacts are dropped from the
        user's main roster (used by account deletion)."""
        db_jids = [str(ojid) for (ojid,) in self.db.fetchall(
            "SELECT jid FROM rosters WHERE user_id=?", (str(uid),))]

        # The guest's own account is never a roster contact on the host
        # side, so its presence echo must not be replayed as a virtual
        # contact going offline. Exclude it from every source below.
        self_bare = (str(client.client_jid.bare)
                     if client is not None else None)

        # Collect every candidate (contact, resource) we might have made
        # visible to the host. The authoritative source is the component
        # level forwarded-presence registry; the per-client caches and the
        # bare JIDs from db.rosters are kept as fallbacks.
        full_jids = []
        registered = self.drainPresenceResources(uid)
        for j in registered:
            if self_bare is None or str(JID(j).bare) != self_bare:
                full_jids.append(str(j))
        if client is not None:
            for j in client.virtual_contacts:
                if self_bare is None or str(JID(j).bare) != self_bare:
                    full_jids.append(j)
            for j in client.presences.keys():
                if self_bare is None or str(JID(j).bare) != self_bare:
                    full_jids.append(str(j))
            for j in client.presences_available_full:
                if self_bare is None or str(JID(j).bare) != self_bare:
                    full_jids.append(str(j))
        self.debug.logger.debug(
            "offlineUser: uid=%s host=%s, %d registered, %d cached "
            "presences, %d available_full, %d entries in db.rosters, "
            "candidates=%s",
            uid, host_jid.bare, len(registered),
            len(client.presences) if client is not None else 0,
            len(client.presences_available_full)
            if client is not None else 0, len(db_jids), sorted(set(full_jids)))

        sent_quoted = set()
        sent_bares = set()
        # NB: a fresh stanza object per send. slixmpp queues stanza
        # OBJECTS and serializes them later, so mutating one shared
        # instance between sends would emit the final field values on
        # every queued stanza.
        for guest_jid in full_jids:
            quoted = self.quoteJID(guest_jid)
            if quoted in sent_quoted:
                continue
            self.make_presence(ptype="unavailable", pto=host_jid.full,
                               pfrom=quoted).send()
            sent_quoted.add(quoted)
            sent_bares.add(guest_jid.split('/', 1)[0])
        for guest_jid in db_jids:
            if self_bare is not None and guest_jid == self_bare:
                continue
            if guest_jid in sent_bares:
                continue
            quoted = self.quoteJID(guest_jid)
            if quoted in sent_quoted:
                continue
            self.make_presence(ptype="unavailable", pto=host_jid.full,
                               pfrom=quoted).send()
            sent_quoted.add(quoted)
        if remove:
            for guest_jid in db_jids:
                quoted = self.quoteJID(guest_jid)
                for ptype in ("unsubscribe", "unsubscribed"):
                    self.make_presence(ptype=ptype, pto=host_jid.full,
                                       pfrom=quoted).send()
        self.make_presence(ptype="unavailable", pto=host_jid.full,
                           pfrom=self.cJid, pstatus="Disconnected").send()
        if remove:
            for ptype in ("unsubscribe", "unsubscribed"):
                self.make_presence(ptype=ptype, pto=host_jid.full,
                                   pfrom=self.cJid).send()

    def shutdownHandler(self, signum=None, frame=None):
        if self.shuttingDown:
            self.loop.stop()
            return
        self.shuttingDown = True
        self.debug.logger.info(
            "Transport shutdown requested; taking %d active sessions offline",
            len(self.clients))

        async def finish_shutdown():
            clients = list(self.clients.values())
            try:
                # Send resource-specific unavailable stanzas before closing
                # the component stream, then let every guest stream finish.
                for cl in clients:
                    if cl.uid:
                        self.offlineUser(
                            cl.uid, cl.host_jid, client=cl, remove=False)
                guest_disconnects = [
                    cl.disconnect(wait=2) for cl in clients
                    if cl.connected or cl.authenticated]
                if guest_disconnects:
                    await asyncio.gather(*guest_disconnects,
                                         return_exceptions=True)
                await self.disconnect(wait=2)
            finally:
                self.debug.logger.info("Transport shutdown complete")
                self.loop.stop()

        self.loop.create_task(finish_shutdown())

    # ---- JID quoting ----

    def quoteJID(self, ujid):
        return utils.quoteJID(ujid, self.cJid)

    def unquoteJID(self, qjid):
        return utils.unquoteJID(qjid, self.cJid)

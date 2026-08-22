# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the guest C2S connection.

import copy
import socket
import uuid

from slixmpp import ClientXMPP
from slixmpp.jid import InvalidJID, JID
from slixmpp.xmlstream import ET
from slixmpp.xmlstream.matcher import StanzaPath
from slixmpp.xmlstream.handler import Callback

import utils
from roster import Roster


def build_roster_exchange(from_jid, to_jid, items, group):
    """XEP-0144 roster item exchange stanza (the iq-set variant used
    by legacy transports): *items* is an iterable of (jid, name)
    pairs; all items are offered for addition into *group*."""
    iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
    iq.set("type", "set")
    iq.set("to", str(to_jid))
    iq.set("from", str(from_jid))
    iq.set("id", uuid.uuid4().hex)
    x = utils.addsub(iq, "x", "http://jabber.org/protocol/rosterx")
    for jid, name in items:
        item = utils.addsub(x, "item",
                            "http://jabber.org/protocol/rosterx")
        item.set("action", "add")
        item.set("jid", str(jid))
        if name:
            item.set("name", name)
        if group:
            g = utils.addsub(item, "group",
                             "http://jabber.org/protocol/rosterx")
            g.text = group
    return iq

class GuestClient(ClientXMPP):
    PING_INTERVAL = 60

    def __init__(self, uid, el, component, host_jid, client_jid,
                 server, secret, port=5222, import_roster=False,
                 remove_from_roster=False, import_group=None,
                 test_mode=False):
        ClientXMPP.__init__(self, client_jid.full, secret)

        self.uid = uid
        self.config = component.config
        self.xmlstream = self
        self.isGTalk = False
        self.presences = {}
        self.presences_available = []
        self.presences_available_full = []
        self.alreadyReply = []
        self.component = component
        self.connected = False
        self.authenticated = False
        self.host_jid = host_jid
        self.guest_roster = Roster(self)
        self.server = server
        self.port = port
        self.import_roster = import_roster
        self.remove_from_roster = remove_from_roster
        self.import_group = import_group
        self.client_jid = client_jid
        self.need_disconnect = False
        self.error = None
        self.secret = secret
        self.presenceSent = False
        self.startPresence = el
        self.ping_obj = None

        self.default_domain = server
        self.default_port = port

        # Disable slixmpp's automatic subscription handling: J2J
        # performs its own roster/subscription management.
        self.auto_authorize = None
        self.auto_subscribe = False

        # Legacy C2S ports serve plaintext/STARTTLS only: skip the
        # direct-TLS handshake attempt (it aborts the whole attempt
        # loop via our onConnectFailed handler) and allow plain text
        # as a last resort.
        self.enable_direct_tls = False
        self.enable_plaintext = True

        self.add_event_handler('session_start', self.onSessionStart)
        self.add_event_handler('presence', self.onPresence)
        self.add_event_handler('roster_update', self.onRosterResult)
        self.add_event_handler('disconnected', self.onDisconnected)
        self.add_event_handler('connection_failed', self.onConnectFailed)
        self.register_handler(
            Callback('GuestMessage', StanzaPath('message'), self.onMessage))
        self.register_handler(
            Callback('GuestIq', StanzaPath('iq'), self.onIq))

        self.component.debug.loginsLog(
            "User %s is connecting to %s:%s with guest-jid %s" %
            (host_jid.full, server, str(port), client_jid.full))

        if not test_mode:
            # Prefer an explicit IPv4 address when connecting to the remote
            # server: avoids hard failures on dual-stack hosts without an
            # IPv6 route (AAAA tried first would fail with ENETUNREACH).
            addr = None
            try:
                infos = socket.getaddrinfo(server, int(port),
                                           socket.AF_INET, socket.SOCK_STREAM)
                if infos:
                    addr = infos[0][4][0]
            except Exception:
                addr = None
            if addr:
                self.connect(addr, int(port))
            else:
                self.connect()

    # ---- XML debug logging ----

    def incoming_filter(self, xml):
        self.component.debug.clientsXmlsLog(
            utils.tostring(xml), self.client_jid, self.host_jid)
        return ClientXMPP.incoming_filter(self, xml)

    def send_raw(self, data):
        self.component.debug.clientsXmlsLog(
            data, self.client_jid, self.host_jid, out=True)
        return ClientXMPP.send_raw(self, data)

    # ---- stream lifecycle ----

    def onSessionStart(self, event):
        if self.need_disconnect:
            self.disconnect()
            return

        if self.startPresence is not None:
            xml = copy.deepcopy(self.startPresence.xml)
            for attr in list(xml.attrib):
                del xml.attrib[attr]
            self.send(utils.tostring(
                utils.retag(xml, utils.COMPONENT_NS, utils.CLIENT_NS)))

        self.get_roster()

        self.authenticated = True
        self.connected = True
        self.ping()

    def ping(self):
        try:
            self.send_raw(b' ')
        except Exception:
            return
        if not self.need_disconnect:
            self.ping_obj = self.loop.call_later(self.PING_INTERVAL,
                                                 self.ping)

    def onConnectFailed(self, event):
        self.component.debug.loginErrorLog(
            "User %s has error in connection:\n%s" %
            (self.host_jid.full, str(event)))
        self.cancel_connection_attempt()
        error = "remote-server-not-found"
        cond = "cancel"
        self.component.sendError(self.startPresence, cond, error)
        self.component.deleteClient(self.host_jid)

    def onDisconnected(self, event):
        if self.ping_obj:
            try:
                self.ping_obj.cancel()
            except Exception:
                pass
            self.ping_obj = None
        if not self.error:
            presence = self.component.make_presence(
                ptype='unavailable',
                pto=self.host_jid.full,
                pfrom=self.component.cJid,
                pstatus='Disconnected')
            presence.send()
        uid = self.component.db.getIdByJid(self.host_jid.bare)
        if (self.presences_available_full or not self.presences) and uid:
            unPres = self.component.make_presence(
                ptype='unavailable', pto=self.host_jid.full)
            for ojid in self.presences_available_full:
                unPres['from'] = self.component.quoteJID(ojid)
                unPres.send()
            for ojid in self.presences.keys():
                if self.component.db.getCount(
                        'rosters', 'user_id=? AND jid=?',
                        (str(uid), ojid.split("/")[0])):
                    unPres['from'] = self.component.quoteJID(ojid)
                    unPres.send()
        self.component.deleteClient(self.host_jid)

    # ---- roster ----

    def onRosterResult(self, iq):
        self.guest_roster.updateFromClientRoster()

        if not self.presenceSent:
            presence = self.component.make_presence(
                ptype='available',
                pto=self.host_jid.full,
                pfrom=self.component.cJid,
                pstatus='Online')
            presence.send()
            self.presenceSent = True

        db = self.component.db
        uid = db.getIdByJid(self.host_jid.bare)
        if uid and self.import_roster in (1, 2):
            dbroster = [str(jid) for jid, in
                        db.fetchall("SELECT jid FROM rosters WHERE user_id=?", (uid,))]
            presence = self.component.make_presence(
                ptype='unsubscribe', pto=self.host_jid.bare)
            for jid in dbroster:
                if not jid in self.guest_roster.items:
                    presence['from'] = self.component.quoteJID(jid)
                    presence.send()
                    presence['type'] = 'unsubscribed'
                    presence.send()
                    presence['type'] = 'unsubscribe'
                    db.execute("DELETE FROM rosters WHERE user_id=? AND jid=?", (uid, jid))
            missing = [(jid, info)
                       for jid, info in
                       sorted(self.guest_roster.items.items())
                       if str(jid) not in dbroster]
            if not missing:
                return
            if self.import_roster == 1:
                self._importViaSubscriptions(missing)
            else:
                self._importViaRosterExchange(missing)
            for jid, _info in missing:
                db.execute(
                    "INSERT INTO rosters (user_id,jid) VALUES (?,?)",
                    (str(uid), jid))
            db.commit()

    def _importViaSubscriptions(self, missing):
        """Legacy mechanism: one stanza-level subscribe per guest
        contact, sent on the contact's behalf to the host account."""
        for jid, info in missing:
            presence = self.component.make_presence(
                ptype='subscribe', pto=self.host_jid.bare)
            presence['from'] = self.component.quoteJID(jid)
            if info[0]:
                utils.addsub(
                    presence.xml, 'nick',
                    'http://jabber.org/protocol/nick',
                    text=info[0])
            presence.send()

    def _importViaRosterExchange(self, missing):
        """XEP-0144: a single roster item exchange stanza offering
        all new contacts at once, grouped as requested."""
        group = self.import_group or \
            self.component.config.ROSTER_GROUP_NAME
        items = [(jid, info[0]) for jid, info in missing]
        iq = build_roster_exchange(self.component.cJid,
                                   self.host_jid.full, items, group)
        self.component.send(utils.tostring(iq))

    # ---- stanzas ----

    def onMessage(self, el):
        self.route(el)

    def onPresence(self, pres):
        fro = pres['from']
        presType = pres['type']
        if not fro:
            return
        uid = self.component.db.getIdByJid(self.host_jid.bare)
        if not uid:
            return
        isInRoster = self.component.db.getCount(
            "rosters", "user_id=? AND jid=?", (str(uid), fro.bare))
        if presType == "available" or presType == "":
            self.presences[fro.full] = pres
            if isInRoster == 0 and \
               (not fro.bare in self.presences_available):
                return
        elif presType == "unavailable":
            if fro.full in self.presences:
                del self.presences[fro.full]
            if isInRoster == 0 and \
               (not fro.bare in self.presences_available):
                return
        elif presType == "error":
            if isInRoster == 0 and \
               (not fro.bare in self.presences_available):
                return
        self.route(pres)

    def onIq(self, el):
        iqId = el['id'] or None
        iqType = el['type'] or None
        if iqId and iqId in self.component.adhoc.vCardSids \
           and iqType == "result":
            if self.component.adhoc.vCardSids[iqId][0].full == \
               self.host_jid.full:
                del self.component.adhoc.vCardSids[iqId]
                return

        for query in list(el.xml):
            local = query.tag.split('}', 1)[-1]
            ns = query.tag.split('}')[0][1:] if '}' in query.tag else ''
            if ns == "jabber:iq:roster":
                return
            if local == "query" and \
               ns == "http://jabber.org/protocol/disco#items":
                for node in query:
                    if 'jid' in node.attrib:
                        node.attrib['jid'] = self.component.quoteJID(
                            node.attrib['jid'])
            if local == "query" and ns == "jabber:iq:gateway":
                for node in query:
                    if (node.tag.split('}', 1)[-1] == 'jid' and
                            node.text):
                        node.text = self.component.quoteJID(node.text)

        self.route(el)

    def route(self, el):
        fro = el['from']
        # NB: slixmpp returns an empty JID object (truthy!) when the
        # attribute is absent, so check the string value instead.
        if not fro or not fro.full:
            return
        to = el['to']
        try:
            fro = JID(fro)
            if to:
                to = JID(to)
        except InvalidJID:
            return
        el['from'] = self.component.quoteJID(fro.full)
        if not to or to.full == to.bare:
            el['to'] = self.host_jid.bare
        else:
            el['to'] = self.host_jid.full
        uid = self.component.db.getIdByJid(self.host_jid.bare)
        if not uid:
            return
        opts = self.component.db.getOptsById(uid)
        if opts[2] and (el.name == "message" or el.name == "iq"):
            # only roster
            if not (fro.bare in self.guest_roster.items):
                return
        if opts[3]:  # autoreplyenabled
            flag = False
            if el.name == "message" and \
               el['type'] != "groupchat" and \
               el['type'] != "headline" and el['body']:
                flag = True
            if el.name == "presence" and el['type'] == "subscribe":
                flag = True
                pres = self.make_presence(
                    ptype='unsubscribed', pto=fro.bare)
                pres.send()
            if (not fro.full in self.alreadyReply) and flag:
                msg = self.make_message(
                    mto=fro.full, mtype='normal',
                    msubject='J2J Auto Reply Service',
                    mbody=opts[0])
                msg.send()
                self.alreadyReply.append(fro.full)
            if not opts[1]:  # autoreplybutforward
                return

        xml = utils.retag(el.xml, utils.CLIENT_NS, utils.COMPONENT_NS)
        self.component.send(utils.tostring(xml))

    def sendError(self, el, etype, condition):
        node = el.xml if hasattr(el, 'xml') else el
        err = copy.deepcopy(node)
        src_from = node.get('from')
        src_to = node.get('to')
        if src_to is not None:
            err.set('from', src_to)
        if 'from' in err.attrib:
            del err.attrib['from']
        if src_from is not None:
            err.set('to', src_from)
        err.set('type', 'error')
        error = ET.SubElement(err,
                              '{' + utils.CLIENT_NS + '}error')
        error.set('type', etype)
        error.set('code', str(utils.errorCodeMap[condition]))
        ET.SubElement(error,
                      '{urn:ietf:params:xml:ns:xmpp-stanzas}%s' % condition)
        self.send(utils.tostring(err))
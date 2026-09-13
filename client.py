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
import i18n
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

def build_roster_exchange_removal(from_jid, to_jid, jids, group=None):
    """XEP-0144 roster item exchange message suggesting the deletion of
    *jids* from the user's roster (the message variant recommended for
    delete suggestions). The receiving application matches each item
    against the roster *group*, so it must be the same group the contact
    was originally offered into."""
    msg = utils.addsub(None, "message", utils.COMPONENT_NS)
    msg.set("type", "normal")
    msg.set("to", str(to_jid))
    msg.set("from", str(from_jid))
    msg.set("id", uuid.uuid4().hex)
    x = utils.addsub(msg, "x", "http://jabber.org/protocol/rosterx")
    for jid in jids:
        item = utils.addsub(x, "item",
                            "http://jabber.org/protocol/rosterx")
        item.set("action", "delete")
        item.set("jid", str(jid))
        if group:
            g = utils.addsub(item, "group",
                             "http://jabber.org/protocol/rosterx")
            g.text = group
    return msg

def _carbonChild(el):
    """Detect an XEP-0280 wrapper in *el*. Returns (direction, inner)
    where direction is "sent"/"received" and inner is the forwarded
    <message/> element (or None), or (None, None) when *el* is a
    regular message."""
    xml = el.xml if hasattr(el, 'xml') else el
    node = xml.find('{%s}sent' % utils.CARBONS_NS)
    direction = "sent"
    if node is None:
        node = xml.find('{%s}received' % utils.CARBONS_NS)
        direction = "received"
    if node is None:
        return None, None
    inner = None
    forwarded = node.find('{%s}forwarded' % utils.FORWARD_NS)
    if forwarded is not None:
        inner = forwarded.find('{%s}message' % utils.CLIENT_NS)
    return direction, inner

class GuestClient(ClientXMPP):
    PING_INTERVAL = 60
    # XEP-0198 resumption window: on an unexpected guest stream loss we
    # keep the host-side contacts online and reconnect up to
    # RESUME_MAX_ATTEMPTS times, waiting RESUME_BASE_DELAY seconds after
    # the first drop and growing arithmetically up to RESUME_MAX_DELAY.
    RESUME_BASE_DELAY = 10
    RESUME_MAX_DELAY = 60
    RESUME_MAX_ATTEMPTS = 6

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
        # Resources of virtual contacts that we actually forwarded to the
        # host this session. This -- not the fragile presence cache -- is
        # the authoritative set of (contact, resource) pairs to take
        # offline, since it survives the guest stream being torn down.
        self.virtual_contacts = set()
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
        # XEP-0280: set once the remote server confirms <enable/>.
        self.carbons_enabled = False
        # XEP-0198: set once the current stream negotiated stream
        # management with the guest server (the precondition for
        # resumption). Cleared on sm_failed and never trusted during the
        # resumption window itself.
        self.sm_enabled = False
        # True while the guest stream is down and we are trying to resume
        # it (contacts stay online at the host until we give up).
        self.resuming = False
        self.resume_attempts = 0
        self.resume_timer = None

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

        self.register_plugin('xep_0280')
        self.register_plugin('xep_0198')

        self.add_event_handler('session_start', self.onSessionStart)
        self.add_event_handler('presence', self.onPresence)
        self.add_event_handler('roster_update', self.onRosterResult)
        self.add_event_handler('disconnected', self.onDisconnected)
        self.add_event_handler('connection_failed', self.onConnectFailed)
        self.add_event_handler('sm_enabled', self._onSmEnabled)
        self.add_event_handler('session_resumed', self._onSessionResumed)
        self.add_event_handler('sm_failed', self._onSmFailed)
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
            # Remember the exact connect arguments so the XEP-0198
            # resumption retry reconnects to the same endpoint.
            self._resume_connect_args = (addr, int(port))
            if addr:
                self.connect(addr, int(port))
            else:
                self.connect()
        else:
            self._resume_connect_args = (None, None)

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

        # Detect silently dead guest links (no RST/FIN -- NAT timeouts,
        # crashed hosts) via OS keepalive probes.
        if self.transport is not None:
            sock = self.transport.get_extra_info('socket')
            if sock is not None:
                utils.enableTcpKeepalive(sock)

        if self.startPresence is not None:
            xml = copy.deepcopy(self.startPresence.xml)
            for attr in list(xml.attrib):
                del xml.attrib[attr]
            self.send(utils.tostring(
                utils.retag(xml, utils.COMPONENT_NS, utils.CLIENT_NS)))

        self.get_roster()
        self._enableCarbons()

        self._finishResumeRecovery()

    def ping(self):
        if self.ping_obj is not None:
            try:
                self.ping_obj.cancel()
            except Exception:
                pass
            self.ping_obj = None
        try:
            self.send_raw(b' ')
        except Exception:
            return
        if not self.need_disconnect:
            self.ping_obj = self.loop.call_later(self.PING_INTERVAL,
                                                 self.ping)

    def onConnectFailed(self, event):
        if self.resuming:
            # A retry attempt failed: stop slixmpp's own rescheduling (we
            # drive the backoff ourselves) and schedule the next retry.
            self.component.debug.logger.debug(
                "Guest stream reconnect failed for %s: %s",
                self.host_jid.full, event)
            self.cancel_connection_attempt()
            self._scheduleResumeAttempt()
            return
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
        if self.need_disconnect:
            # The user logged out, the account was suspended or deleted:
            # never reconnect behind their back.
            self._teardown()
            return
        if self.resuming:
            # A drop while retrying (the attempt's own connection died
            # before feature negotiation): push the next retry unless one
            # is already pending.
            if self.resume_timer is None:
                self._scheduleResumeAttempt()
            return
        if not self.sm_enabled:
            # The guest server never granted stream management, so there is
            # nothing to resume: legacy behaviour (immediate offline).
            self._teardown()
            return
        self._enterResume()

    # ---- XEP-0198 stream resumption ----

    def _onSmEnabled(self, event):
        self.sm_enabled = True
        self.component.debug.logger.debug(
            "XEP-0198 enabled for guest stream of %s", self.host_jid.full)

    def _onSmFailed(self, event):
        self.sm_enabled = False

    def _onSessionResumed(self, event):
        self.component.debug.logger.info(
            "Guest stream resumed via XEP-0198 for %s", self.host_jid.full)
        self._finishResumeRecovery()

    def _enterResume(self):
        """Start a bounded retry window after an unexpected guest stream
        loss. Contacts stay online at the host and stanzas addressed to the
        guest are buffered by slixmpp until the stream is restored or the
        window expires."""
        if self.need_disconnect or self.component.shuttingDown:
            self._teardown()
            return
        self.resuming = True
        self.resume_attempts = 0
        self.component.debug.logger.info(
            "Guest stream for %s lost; keeping host-side contacts online and "
            "retrying the connection (XEP-0198 resumption)",
            self.host_jid.full)
        self._scheduleResumeAttempt()

    def _scheduleResumeAttempt(self):
        if self.resume_timer is not None:
            return
        if self.need_disconnect or self.component.shuttingDown:
            self._teardown()
            return
        delay = min(self.RESUME_BASE_DELAY * (self.resume_attempts or 1),
                    self.RESUME_MAX_DELAY)
        self.resume_timer = self.loop.call_later(delay,
                                                 self._doResumeAttempt)

    def _doResumeAttempt(self):
        self.resume_timer = None
        if self.need_disconnect or self.component.shuttingDown:
            self._teardown()
            return
        self.resume_attempts += 1
        if self.resume_attempts > self.RESUME_MAX_ATTEMPTS:
            self.component.debug.logger.info(
                "Giving up reconnecting the guest stream of %s after %d "
                "attempts; taking virtual contacts offline",
                self.host_jid.full, self.resume_attempts - 1)
            self._teardown()
            return
        self.component.debug.logger.info(
            "Reconnect attempt %d/%d for the guest stream of %s",
            self.resume_attempts, self.RESUME_MAX_ATTEMPTS,
            self.host_jid.full)
        try:
            self._connect_loop_wait = 0
            self.connect(*self._resume_connect_args)
        except Exception as exc:
            self.component.debug.logger.debug(
                "connect() raised during resumption for %s: %s",
                self.host_jid.full, exc)
            self._scheduleResumeAttempt()

    def _finishResumeRecovery(self):
        """Called when the guest stream is back (either resumed via
        XEP-0198 or re-established from scratch). Restores the connected
        state, restarts the whitespace keepalive and ends the retry
        window."""
        if self.resume_timer is not None:
            try:
                self.resume_timer.cancel()
            except Exception:
                pass
            self.resume_timer = None
        recovering = self.resuming
        self.resuming = False
        self.resume_attempts = 0
        self.authenticated = True
        self.connected = True
        if recovering:
            self.component.debug.logger.info(
                "Guest stream recovered for %s", self.host_jid.full)
        self.ping()

    def _teardown(self):
        """Final teardown of a guest session: cancel any pending
        resumption, take every virtual contact (and the transport itself)
        offline at the host via db.rosters coverage, and drop the session
        from self.clients."""
        self.resuming = False
        self.resume_attempts = 0
        if self.resume_timer is not None:
            try:
                self.resume_timer.cancel()
            except Exception:
                pass
            self.resume_timer = None
        try:
            self.cancel_connection_attempt()
        except Exception:
            pass
        uid = self.component.db.getIdByJid(self.host_jid.bare)
        if uid:
            self.component.offlineUser(
                uid, self.host_jid, client=self, remove=False)
        self.component.deleteClient(self.host_jid)

    # ---- roster ----

    def onRosterResult(self, iq):
        self.guest_roster.updateFromClientRoster()

        if not self.presenceSent:
            lang = self.component.getUserLang(self.host_jid.bare)
            presence = self.component.make_presence(
                ptype='available',
                pto=self.host_jid.full,
                pfrom=self.component.cJid,
                pstatus=i18n.t(lang, "status_online") % self.client_jid.bare)
            presence.send()
            self.presenceSent = True

        db = self.component.db
        uid = db.getIdByJid(self.host_jid.bare)
        if uid and self.import_roster in (1, 2):
            opts = db.getOptsById(uid)
            rostersync = opts[10] if (len(opts) > 10 and
                                      opts[10] is not None) else 1
            # The virtual JID of the connected (guest) account must never be
            # offered as a contact to the main roster.
            self_jids = {str(self.client_jid.bare)}
            dbroster = set(str(jid) for jid, in
                          db.fetchall("SELECT jid FROM rosters WHERE user_id=?", (uid,)))
            # Contacts that disappeared from the guest roster while the
            # transport was offline (or mid-session). Offer their removal
            # through the same mechanism that added them: presence
            # unsubscribe pairs for the legacy subscription mode, an
            # XEP-0144 delete suggestion otherwise.
            removed = [jid for jid in sorted(dbroster)
                       if jid not in self.guest_roster.items
                       and jid not in self_jids]
            if removed:
                if self.import_roster == 1:
                    # NB: a fresh stanza object per send -- slixmpp queues
                    # stanza objects and serializes them later, so mutating
                    # one shared instance between sends would emit the final
                    # field values.
                    for jid in removed:
                        quoted = self.component.quoteJID(jid)
                        for ptype in ('unsubscribe', 'unsubscribed'):
                            self.component.make_presence(
                                ptype=ptype, pto=self.host_jid.bare,
                                pfrom=quoted).send()
                else:
                    self._removeViaRosterExchange(removed)
                # Strict mirror: db.rosters tracks the real guest roster.
                # Before dropping a removed contact's row, extinguish any
                # presence it may still have at the host (resource-level
                # from this session's registry, bare as fallback) so the
                # contact cannot linger as an online ghost afterwards.
                for jid in removed:
                    quoted = self.component.quoteJID(jid)
                    registered = self.component.presence_resources.get(uid)
                    if registered:
                        for full in list(registered):
                            if str(JID(full).bare) == jid:
                                self.component.make_presence(
                                    ptype="unavailable",
                                    pto=self.host_jid.full,
                                    pfrom=self.component.quoteJID(
                                        full)).send()
                                self.component.notePresenceWithdrawn(
                                    uid, full)
                    self.component.make_presence(
                        ptype="unavailable", pto=self.host_jid.bare,
                        pfrom=quoted).send()
                    db.execute("DELETE FROM rosters "
                               "WHERE user_id=? AND jid=?",
                               (str(uid), jid))
            if rostersync:
                # Authoritative sync: offer every guest contact (except the
                # self-contact) on each login, so removed contacts reappear.
                missing = [(jid, info)
                           for jid, info in
                           sorted(self.guest_roster.items.items())
                           if str(jid) not in self_jids]
            else:
                # Legacy behaviour: only contacts not imported before.
                missing = [(jid, info)
                           for jid, info in
                           sorted(self.guest_roster.items.items())
                           if str(jid) not in dbroster
                           and str(jid) not in self_jids]
            if missing:
                if self.import_roster == 1:
                    self._importViaSubscriptions(missing)
                else:
                    self._importViaRosterExchange(missing)
            if rostersync:
                # db.rosters mirrors the real guest roster: additions are
                # recorded here, removals pruned in the block above (with
                # presence extinguished first). The self-contact is never
                # recorded.
                for jid, _info in missing:
                    if db.getCount('rosters', 'user_id=? AND jid=?',
                                   (str(uid), jid)) == 0:
                        db.execute(
                            "INSERT INTO rosters (user_id,jid) VALUES (?,?)",
                            (str(uid), jid))
            else:
                # Legacy: only record the newly imported contacts; already
                # imported ones stay in db.rosters so they are not re-sent.
                for jid, _info in missing:
                    if db.getCount('rosters', 'user_id=? AND jid=?',
                                   (str(uid), jid)) == 0:
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
        items = [(self.component.quoteJID(jid), info[0])
                 for jid, info in missing]
        iq = build_roster_exchange(self.component.cJid,
                                   self.host_jid.full, items, group)
        self.component.send(utils.tostring(iq))

    def _removeViaRosterExchange(self, removed):
        """XEP-0144: a single message suggesting the deletion of every
        guest-roster contact that is no longer present on the guest
        account from the user's main roster."""
        group = self.import_group or \
            self.component.config.ROSTER_GROUP_NAME
        jids = [self.component.quoteJID(jid) for jid in removed]
        msg = build_roster_exchange_removal(
            self.component.cJid, self.host_jid.full, jids, group)
        self.component.send(utils.tostring(msg))

    # ---- stanzas ----

    def onMessage(self, el):
        direction, inner = _carbonChild(el)
        if direction == "sent":
            self._mirrorSentCarbon(inner)
            return
        if direction == "received":
            # A copy of a message another resource of this account has
            # received: the guest stream gets the original through
            # normal fan-out, so relaying the copy would duplicate it
            # at the host.
            self.component.debug.logger.debug(
                "Dropping carbon <received> duplicate for %s",
                self.host_jid.full)
            return
        self.route(el)

    def _enableCarbons(self):
        """Best-effort XEP-0280 activation. When the remote server
        supports carbons, messages the user writes from its other
        clients arrive here as <sent> copies and can be mirrored to
        the host side."""
        try:
            future = self['xep_0280'].enable(timeout=15)
        except Exception:
            return

        def done(fut):
            try:
                fut.result()
            except Exception as exc:
                self.component.debug.logger.debug(
                    "Carbons unavailable for %s: %s",
                    self.host_jid.full, exc)
            else:
                self.carbons_enabled = True

        future.add_done_callback(done)

    def _mirrorSentCarbon(self, inner):
        """Relay a <sent> carbon -- a chat message the user wrote from
        another client on the remote server -- to the host as a proper
        carbon copy. The mirror goes to the host only; it is never
        re-sent to the real recipient (no duplicates, no loops)."""
        if not self.carbons_enabled or inner is None:
            return
        if inner.get("type") not in (None, "", "chat"):
            return
        body = inner.find('{%s}body' % utils.CLIENT_NS)
        if body is None or not (body.text or "").strip():
            return
        frm = inner.get("from")
        to = inner.get("to")
        if not frm or not to:
            return
        try:
            fjid = JID(frm)
            tjid = JID(to)
        except InvalidJID:
            return
        # The sender must be this account itself and the recipient a
        # real remote entity (not the account, not a bare domain).
        if fjid.bare != self.client_jid.bare:
            return
        if not tjid.bare or tjid.bare == self.client_jid.bare or \
                '@' not in tjid.bare:
            return
        uid = self.component.db.getIdByJid(self.host_jid.bare)
        if not uid:
            return
        opts = self.component.db.getOptsById(uid)
        # Respect the "only roster contacts" privacy gate.
        if opts[2] and tjid.bare not in self.guest_roster.items:
            return
        wrap = utils.addsub(None, "message", utils.COMPONENT_NS)
        wrap.set("type", "chat")
        wrap.set("from", str(self.host_jid.bare))
        wrap.set("to", str(self.host_jid.full))
        wrap.set("id", uuid.uuid4().hex)
        sent = utils.addsub(wrap, "sent", utils.CARBONS_NS)
        forwarded = utils.addsub(sent, "forwarded", utils.FORWARD_NS)
        # Inner addresses use host-side identities: from is the user
        # themselves, to the contact's virtual JID, so carbon-aware
        # clients render the copy inside the right chat window as an
        # outgoing message.
        mirror = utils.addsub(forwarded, "message", utils.CLIENT_NS)
        mirror.set("type", "chat")
        mirror.set("from", str(self.host_jid.bare))
        mirror.set("to", self.component.quoteJID(tjid.full))
        utils.addsub(mirror, "body", utils.CLIENT_NS, text=body.text)
        self.component.send(utils.tostring(wrap))

    def onPresence(self, pres):
        try:
            fro = pres['from']
        except InvalidJID:
            return
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
        if str(fro.bare) != str(self.client_jid.bare):
            self.virtual_contacts.add(fro.full)
            # Mirror the forward into the component-level registry so the
            # (contact, resource) pair survives guest stream teardown and
            # is taken offline on disconnect.
            if presType in ("available", ""):
                self.component.notePresenceForwarded(uid, fro.full)
            elif presType == "unavailable":
                self.component.notePresenceWithdrawn(uid, fro.full)
        self.route(pres)

    def onIq(self, el):
        iqId = el['id'] or None
        iqType = el['type'] or None
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
            if local == "query" and ns == utils.DISCO_INFO_NS and \
                    iqType == "result":
                # Some entities answer vCard requests without advertising
                # vcard-temp in disco#info. Virtual JIDs expose vCard as a
                # proxy, so advertise that capability to the host client.
                if not any(child.get('var') == utils.VCARD_NS
                           for child in query
                           if child.tag.split('}', 1)[-1] == 'feature'):
                    utils.addsub(query, "feature", utils.DISCO_INFO_NS,
                                 {"var": utils.VCARD_NS})
            if local == "query" and ns == "jabber:iq:gateway":
                for node in query:
                    if (node.tag.split('}', 1)[-1] == 'jid' and
                            node.text):
                        node.text = self.component.quoteJID(node.text)

        self.route(el)

    def route(self, el):
        # NB: slixmpp returns an empty JID object (truthy!) when the
        # attribute is absent, so check the string value instead.
        # Reading el['from']/el['to'] itself can raise InvalidJID for a
        # malformed address; a bad stanza must never kill this stream.
        try:
            fro = JID(el['from'])
            to = el['to']
            if not fro or not fro.full:
                return
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
        lang = self.component.getUserLang(self.host_jid.bare)
        if opts[2] and el.name == "message":
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
                        msubject=i18n.t(lang, "auto_reply_subject"),
                    mbody=opts[0])
                msg.send()
                self.alreadyReply.append(fro.full)
            if not opts[1]:  # autoreplybutforward
                return

        xml = utils.retag(el.xml, utils.CLIENT_NS, utils.COMPONENT_NS)
        if (el.name == 'message' and opts is not None and
                not utils.strip_relay_features(
                    xml, bool(opts[7]), bool(opts[8]), bool(opts[9]))):
            return
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

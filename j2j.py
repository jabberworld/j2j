# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

__id__ = "$Id: j2j.py 153 2011-02-16 12:54:49Z binary $"

if __name__ == '__main__':
    print "start main.py"
    sys.exit(0)

import sys
import hashlib
import time
import os
import utils
import codecs #!

from twisted.internet.defer import Deferred
from twisted.words.xish import domish,xpath
from twisted.words.xish.domish import Element
from twisted.words.protocols.jabber import xmlstream, client, jid, component
from twisted.words.protocols.jabber.jid import internJID

import database
import debug
from client import Client
from adhoc import AdHoc

reload(sys)
sys.setdefaultencoding("utf-8")
sys.stdout = codecs.lookup('utf-8')[-1](sys.stdout)

class J2JComponent(component.Service):
    def __init__(self, reactor, version, config, cJid):
        self.config = config
        self.reactor = reactor
        self.adhoc = AdHoc(self)
        self.VERSION = version
        self.cJid = cJid

    def componentConnected(self, xs):
        self.shuttingDown = False
        self.startTime = time.time()
        try:
            for client in self.clients.keys():
                self.clients[client].xmlstream.sendFooter()
            del self.clients
        except:
            pass
        self.clients = {}
        self.debug = debug.Debug(self.config.LOGFILE,
                                self.config.DEBUG_REGISTRATIONS,
                                self.config.DEBUG_LOGINS,
                                self.config.DEBUG_XMLLOG,
                                self.config.DEBUG_COMPXML,
                                self.config.DEBUG_CLXML,
                                self.config.DEBUG_CLXMLACL)
        self.db = database.Database(self.config, self.reactor)
        self.xmlstream = xs
        self.xmlstream.rawDataInFn = self.rawIn
        self.xmlstream.rawDataOutFn = self.rawOut
        self.xmlstream.addObserver("/iq", self.onIq)
        self.xmlstream.addObserver("/presence", self.onPresence)
        self.xmlstream.addObserver("/message", self.onMessage)

        jids = self.db.fetchall('SELECT jid FROM %susers' % \
                                self.db.dbTablePrefix)
        probe = Element((None, 'presence'))
        probe.attributes['type'] = 'probe'
        probe.attributes['from'] = self.cJid
        if self.config.SEND_PROBES:
            for jid, in jids:
                probe.attributes['to'] = jid
                self.send(probe)
        print "Connected"

    def rawIn(self, data):
        self.debug.componentXmlsLog(data)

    def rawOut(self, data):
        self.debug.componentXmlsLog(data, True)

    def onMessage(self, el):
        fro = el.getAttribute("from")
        to = el.getAttribute("to")
        try:
            fro = internJID(fro)
            to = internJID(to)
        except jid.InvalidFormat:
            return
        if to.full() == self.cJid: return
        if not self.clients.has_key(fro.full()):
            pass
        elif not self.clients[fro.full()].authenticated:
            pass
        else:
            self.routeStanza(el,fro,to)
            return
        self.sendError(el, "cancel", "service-unavailable")

    def getClient(self, jid):
        r = None
        jidStr = jid.full()
        if jidStr == jid.userhost():
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

        el.attributes['to'] = self.unquoteJID(to.full())
        del el.attributes['from']
        utils.delUri(el)

        cl.send(el)

    def onPresence(self, el):
        fro = el.getAttribute("from")
        to = el.getAttribute("to")
        presenceType = el.getAttribute("type")
        try:
            fro = internJID(fro)
            to = internJID(to)
        except jid.InvalidFormat:
            return

        if to.full() == self.cJid:
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

        if presenceType == "available" or presenceType == None:
            if not self.clients.has_key(fro.full()): return
            if not self.unquoteJID(to.userhost()) in cl.presences_available:
                cl.presences_available.append(self.unquoteJID(to.userhost()))
            if not self.unquoteJID(to.full()) in cl.presences_available_full:
                cl.presences_available_full.append(self.unquoteJID(to.full()))

        if presenceType == "subscribe":
            toUnq = self.unquoteJID(to.userhost())
            if not self.db.getCount('rosters',
                                    "user_id='%s' AND jid=%s" % \
                                    (str(uid),
                                     self.db.dbQuote(toUnq.encode("utf-8")))):
                self.db.execute("INSERT INTO %s (user_id,jid) \
                                 VALUES ('%s',%s)" % \
                               (self.db.dbTablePrefix+"rosters",
                                str(uid),
                                self.db.dbQuote(toUnq.encode("utf-8"))))
                self.db.commit()
            if cl.roster.items.has_key(toUnq):
                subscription = cl.roster.items[toUnq][1]
                if subscription in ["both", "to"]:
                    p = Element((None,"presence"))
                    p.attributes["to"] = fro.userhost()
                    p.attributes["from"] = to.userhost()
                    p.attributes["type"] = "subscribed"
                    self.send(p)
                    if subscription == "both":
                        p.attributes["type"] = "subscribe"
                        self.send(p)

                    for pr in cl.presences.keys():
                        if pr.split('/')[0] == toUnq:
                            pres = cl.presences[pr]
                            pres.attributes["from"] = self.quoteJID(pr)
                            pres.attributes["to"] = fro.full()
                            utils.delUri(pres)
                            self.send(pres)
                    return

        if presenceType == "unsubscribe" or presenceType == "unsubscribed":
            toUnq = self.unquoteJID(to.full())
            if self.db.getCount('rosters',
                                "user_id='%s' AND jid=%s" % \
                                (str(uid), 
                                 self.db.dbQuote(toUnq.encode("utf-8")))):
                self.db.execute("DELETE FROM %s WHERE \
                                 user_id='%s' AND jid=%s" % \
                                 (self.db.dbTablePrefix+"rosters",
                                  str(uid),
                                  self.db.dbQuote(toUnq.encode('utf-8'))))
                self.db.commit()
                p = Element((None, 'presence'))
                p.attributes["to"] = fro.userhost()
                p.attributes["from"] = to.userhost()
                p.attributes["type"] = "unsubscribed"
                self.send(p)
                if cl.remove_from_roster:
                    cl.roster.removeItem(toUnq)
                else:
                    return

        self.routeStanza(el, fro, to)

    def componentPresence(self, el, fro, presenceType):
        uid = self.db.getIdByJid(fro.userhost())
        if not uid:
            return
        data = self.db.getDataById(uid)
        resource = jid.parse(fro.full())[2]
        if resource == None:
            resource = ''
        else:
            resource = "/" + resource
        try:
            clientJid = jid.JID(data[0] + "@" + data[2] + resource)
        except jid.InvalidFormat:
            self.sendError(el,
                           etype="modify",
                           condition="not-acceptable")
            return
        if data[3] == None or data[3] == '':
            data[3] = data[2]
        try:
            newjid = jid.JID('%s@%s' % (data[0], data[2])).userhost().\
                     encode('utf-8')
        except jid.InvalidFormat:
            return
        newmd5 = hashlib.md5(newjid).hexdigest()
        if not self.clients.has_key(fro.full()) and \
           (presenceType == "available" or presenceType == None):
            self.debug.loginsLog("User %s is trying to log in" % (fro.full()))
            js = []
            utils.delUri(el)
            for element in el.elements():
                if element.name == "x" and element.uri == "j2j:history":
                    try:
                        hops = int(element.attributes["hops"])
                    except:
                        hops = 0
                    if hops > 3:
                        self.sendError(el, "cancel", "not-allowed")
                        return
                    element.attributes["hops"] = str(hops + 1)
                    for jidmd5 in element.elements():
                        if jidmd5.name == "jid":
                            js.append(unicode(jidmd5))
            if not js:
                element = el.addElement("x")
                element.attributes["xmlns"] = "j2j:history"
                element.attributes["hops"] = "1"

            hash = hashlib.md5(fro.userhost().encode('utf-8'))
            jhash = element.addElement("jid", content=hash.hexdigest())
            jhash.attributes["gateway"] = self.cJid

            js.append(hash)
            if newmd5 in js:
                self.sendError(el, "cancel", "conflict")
                self.debug.loginsLog("User %s has confict login:\n%s" % \
                                     (fro.full(), el.toXml()))
                return
            presence = Element((None,'presence'))
            presence.attributes['to'] = fro.full()
            presence.attributes['from'] = self.cJid
            presence.attributes['type'] = 'unavailable'
            presence.addElement('status', content="Logging in...")
            self.send(presence)
            self.clients[fro.full()] = Client(uid,
                                              el,
                                              self.reactor,
                                              self,
                                              fro,
                                              clientJid,
                                              data[3],
                                              data[1],
                                              data[4],
                                              data[5],
                                              data[6])
        elif fro.full() in self.clients and presenceType == "unavailable":
            if self.clients[fro.full()].connected:
                self.debug.loginsLog("User %s is trying to log out" % \
                                      (fro.full()))
                self.clients[fro.full()].xmlstream.sendFooter()
                #del self.clients[fro.full()]
            else:
                self.clients[fro.full()].disconnect = True
        elif fro.full() in self.clients and \
             (presenceType == "available" or presenceType == None):
            if self.clients[fro.full()].connected:
                del el.attributes["to"]
                del el.attributes["from"]
                utils.delUri(el)
                self.clients[fro.full()].send(el)
        elif presenceType == "subscribe":
            presence = Element((None, 'presence'))
            presence.attributes['to'] = fro.full()
            presence.attributes['from'] = self.cJid
            presence.attributes['type'] = 'subscribed'
            self.send(presence)

    def deleteClient(self, jid):
        if self.clients.has_key(jid.full()):
            del self.clients[jid.full()]

    def onIq(self, el):
        fro = el.getAttribute("from")
        to = el.getAttribute("to")
        ID = el.getAttribute("id")
        iqType = el.getAttribute("type")
        try:
            fro = internJID(fro)
            to = internJID(to)
        except jid.InvalidFormat:
            return
        if to.full() == self.cJid:
            return self.componentIq(el, fro, ID, iqType)
        if not self.clients.has_key(fro.full()):
            pass
        elif not self.clients[fro.full()].authenticated:
            pass
        else:
            return self.routeStanza(el, fro, to)
        self.sendError(el, etype="cancel", condition="service-unavailable")

    def componentIq(self,el,fro,ID,iqType):
        for query in el.elements():
            xmlns = query.uri
            node = query.getAttribute("node")

            if xmlns == "vcard-temp" and iqType == "result":
                self.result_vCard(el, fro, ID)
                return

            if xmlns == "jabber:iq:register" and iqType == "get":
                self.getRegister(el, fro, ID)
                return

            if xmlns == "jabber:iq:register" and iqType == "set":
                self.setRegister(el, fro, ID)
                return

            if xmlns == "http://jabber.org/protocol/disco#info" and \
               iqType == "get":
                self.getDiscoInfo(el, fro, ID, node)
                return

            if xmlns == "http://jabber.org/protocol/disco#items" and \
               iqType == "get":
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

            if xmlns == "vcard-temp" and iqType == "get" and \
               query.name == "vCard":
                self.getvcard(fro, ID)
                return

            if xmlns == "http://jabber.org/protocol/commands" and \
               query.name == "command" and iqType == "set":
                etype, condition = self.adhoc.onCommand(query, fro, ID, node)
                if etype is not None:
                    self.sendError(el, etype=etype, condition=condition)
                return

            if xmlns == "http://jabber.org/protocol/stats":
                self.getStats(el, fro, ID)
                return

        self.sendError(el, etype="cancel", condition="feature-not-implemented")

    def result_vCard(self, el, fro, ID):
        if not ID in self.adhoc.vCardSids.keys():
            return
        if fro.userhost() != self.adhoc.vCardSids[ID][0].userhost():
            return
        if not self.adhoc.vCardSids[ID][0].full() in self.clients.keys():
            return
        del el.attributes["to"]
        del el.attributes["from"]
        el.attributes["type"] = "set"
        utils.delUri(el)
        self.clients[self.adhoc.vCardSids[ID][0].full()].xmlstream.send(el)

    def getStats(self, el, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "http://jabber.org/protocol/stats"
        nodes = xpath.XPathQuery(
         "/iq/query[@xmlns='http://jabber.org/protocol/stats']/stat").\
         queryForNodes(el)
        if nodes:
            for node in nodes:
                if node.getAttribute("name") == "users/online":
                    o = query.addElement("stat")
                    o.attributes["name"] = "users/online"
                    o.attributes["units"] = "users"
                    o.attributes["value"] = str(len(self.clients.keys()))
                if node.getAttribute("name") == "users/total":
                    t = query.addElement("stat")
                    t.attributes["name"] = "users/total"
                    t.attributes["units"] = "users"
                    t.attributes["value"] = str(self.db.getCount("users"))
        else:
            query.addElement("stat").attributes["name"] = "users/online"
            query.addElement("stat").attributes["name"] = "users/total"
        self.send(iq)

    def getvcard(self, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        vcard = iq.addElement("vCard")
        vcard.attributes["xmlns"] = "vcard-temp"
        vcard.addElement("NICKNAME", content="J2J")
        vcard.addElement("DESC",
                         content="\
Jabber-To-Jabber Transport (GTalk, LiveJournal inside)\n\
Description: http://wiki.JRuDevels.org/index.php/J2J")
        vcard.addElement("URL", content="http://JRuDevels.org")
        self.send(iq)

    def getRegister(self, el, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "jabber:iq:register"
        uid = self.db.getIdByJid(fro.userhost())
        if uid:
            edit = True
            data = self.db.getDataById(uid)
            query.addElement("registered")
        else:
            edit = False
            data = [None, None, None, None, 5222, False, False]
        form = utils.createForm(query,"form")
        utils.addTitle(form, "J2J Registration Form")
        if not edit:
            utils.addLabel(form, "Please enter data for your Jabber-account")
        else:
            utils.addLabel(form, "Please edit data")
        utils.addTextBox(form, "username", "Username", data[0], required=True)
        utils.addTextPrivate(form, "password", "Password", data[1],
                             required=True)
        utils.addTextBox(form, "server", "Server", data[2], required=True)
        utils.addTextBox(form, "domain", "Domain or IP", data[3])
        utils.addTextBox(form, "port", "Port", str(data[4]))
        if not uid:
            utils.addCheckBox(form, "import_roster", "Import roster", data[5])
        utils.addCheckBox(form, "remove_from_roster",
                          "Remove contacts from guest roster automatically",
                          data[6])
        self.send(iq)

    def setRegister(self, el, fro, ID):
        uid = self.db.getIdByJid(fro.userhost())
        if uid:
            edit = True
        else:
            edit = False
        if xpath.XPathQuery(
            "/iq/query[@xmlns='jabber:iq:register']/remove").matches(el):
            if not edit:
                self.sendError(el, etype="auth",
                                 condition="registration-required")
                return
            for j in self.clients.keys():
                if j.find(fro.userhost()+"/") == 0:
                    if self.clients[j].connected:
                        self.clients[j].xmlstream.sendFooter()
            unPres = Element((None, "presence"))
            unPres.attributes["to"] = fro.full()
            unPres.attributes["type"] = "unavailable"
            if self.clients.has_key(fro.full()):
                for ojid in self.clients[fro.full()].presences_available_full:
                    unPres.attributes["from"] = self.quoteJID(ojid)
                    self.send(unPres)
            ujids = self.db.fetchall("SELECT jid FROM %s WHERE user_id='%s'" %\
                                   (self.db.dbTablePrefix+"rosters", str(uid)))
            for ojid in ujids:
                unPres.attributes["from"] = self.quoteJID(ojid[0])
                unPres.attributes["type"] = "unsubscribe"
                self.send(unPres)
                unPres.attributes["type"] = "unsubscribed"
                self.send(unPres)
            self.db.execute("DELETE from " + self.db.dbTablePrefix + \
                            "rosters WHERE user_id=" + str(uid))
            self.db.execute("DELETE from " + self.db.dbTablePrefix + \
                            "users_options WHERE user_id=" + str(uid))
            self.db.execute("DELETE from " + self.db.dbTablePrefix + \
                            "users WHERE id=" + str(uid))
            self.db.commit()
            self.sendIqResult(fro.full(),
                              self.cJid,
                              ID,
                              "jabber:iq:register")
            pres = Element((None, "presence"))
            pres.attributes["to"] = fro.full()
            pres.attributes["from"] = self.cJid
            pres.attributes["type"] = "unsubscribe"
            self.send(pres)
            pres.attributes["type"] = "unsubscribed"
            self.send(pres)
            pres.attributes["type"] = "unavailable"
            self.send(pres)
            self.debug.registrationsLog("Client %s is unregistered" % \
                                        fro.full())
            return
        formXPath = "\
/iq\
/query[@xmlns='jabber:iq:register']\
/x[@xmlns='jabber:x:data'][@type='submit']"
        username = xpath.queryForString(formXPath + \
                                        "/field[@var='username']/value", el)
        if username == '':
            self.sendError(el, etype="modify", condition="not-acceptable")
            return
        password = xpath.XPathQuery(formXPath + \
                            "/field[@var='password']/value").queryForString(el)
        if password == '':
            self.sendError(el, etype="modify", condition="not-acceptable")
            return
        server = xpath.XPathQuery(formXPath + \
                              "/field[@var='server']/value").queryForString(el)
        if server == '':
            self.sendError(el, etype="modify", condition="not-acceptable")
            return
        import_roster = xpath.XPathQuery(formXPath + \
                       "/field[@var='import_roster']/value").queryForString(el)
        if import_roster:
            import_roster = utils.strToBool(import_roster)
        else:
            import_roster = False
        remove_from_roster = xpath.XPathQuery(formXPath + \
                  "/field[@var='remove_from_roster']/value").queryForString(el)
        if remove_from_roster:
            remove_from_roster = utils.strToBool(remove_from_roster)
        else:
            remove_from_roster = False
        try:
            hjid = jid.JID(username + "@" + server)
        except:
            self.sendError(el, etype='modify', condition='not-acceptable')
            return
        domain = xpath.XPathQuery(formXPath + \
                              "/field[@var='domain']/value").queryForString(el)
        port = xpath.XPathQuery(formXPath + \
                                "/field[@var='port']/value").queryForString(el)
        try:
            port = int(port)
        except:
            port = 5222
        if not edit:
            self.db.execute("INSERT INTO %susers \
                            (jid, \
                            username, \
                            domain, \
                            server, \
                            password, \
                            port, \
                            import_roster, \
                            remove_from_guest_roster) VALUES \
                            (%s,%s,%s,%s,%s,%s,'%s','%s')" % \
                            (self.db.dbTablePrefix,
                             self.db.dbQuote(fro.userhost().encode('utf-8')),
                             self.db.dbQuote(username.encode('utf-8')),
                             self.db.dbQuote(domain.encode('utf-8')),
                             self.db.dbQuote(server.encode('utf-8')),
                             self.db.dbQuote(password.encode('utf-8')),
                             str(port),
                             str(int(import_roster)),
                             str(int(remove_from_roster))))
            uid = self.db.getIdByJid(fro.userhost())
            self.db.execute("INSERT INTO " + self.db.dbTablePrefix + \
                          "users_options ( user_id ) VALUES  ('"+str(uid)+"')")
            self.db.commit()
            self.sendIqResult(fro.full(), self.cJid, ID, "jabber:iq:register")
            pres=Element((None, "presence"))
            pres.attributes["to"] = fro.userhost()
            pres.attributes["from"] = self.cJid
            pres.attributes["type"] = "subscribe"
            self.send(pres)
            if self.config.ADMINS != [] and self.config.REGISTRATION_NOTIFY:
                msg = Element((None, "message"))
                msg.attributes["type"] = "chat"
                msg.attributes["from"] = self.cJid
                msg.addElement("body",
                               content="\
J2J %s Registration notify:\n\
Host JID:%s\nGuest JID:%s" % (self.cJid,
                              fro.full(),
                              username+"@"+server))
                for ajid in self.config.ADMINS:
                    msg.attributes["to"] = ajid
                    self.send(msg)
            self.debug.registrationsLog(
                                 "User %s is registered to guest-jid %s" % \
                                 (fro.full(), username+"@"+server))
        elif edit:
            data = self.db.getDataById(uid)
            if data[0] != username or data[2] != server:
                a = self.db.fetchall("SELECT jid FROM %s WHERE user_id='%s'" %\
                                (self.db.dbTablePrefix+"rosters", str(uid)))
                for unjid in a:
                    pres = Element((None, "presence"))
                    pres.attributes["to"] = fro.userhost()
                    pres.attributes["from"] = self.quoteJID(unjid[0])
                    pres.attributes["type"] = "unsubscribe"
                    self.send(pres)
                    pres.attributes["type"] = "unsubscribed"
                    self.send(pres)
                self.db.execute("DELETE FROM %s WHERE user_id='%s'" % \
                                (self.db.dbTablePrefix+"rosters", str(uid)))
            self.db.execute("UPDATE %s SET username=%s, \
                                           domain=%s, \
                                           server=%s, \
                                           password=%s, \
                                           port=%s, \
                                           remove_from_guest_roster='%s' \
                                           WHERE id='%s'" % \
                                  (self.db.dbTablePrefix+"users",
                                   self.db.dbQuote(username.encode('utf-8')),
                                   self.db.dbQuote(domain.encode('utf-8')),
                                   self.db.dbQuote(server.encode('utf-8')),
                                   self.db.dbQuote(password.encode('utf-8')),
                                   str(port),
                                   str(int(remove_from_roster)),
                                   str(uid)))
            self.db.commit()
            self.sendIqResult(fro.full(),
                              self.cJid,
                              ID,
                              "jabber:iq:register")
            self.debug.registrationsLog("\
User %s has changed registration information to %s" % (fro.full(),
                                                       username+"@"+server))

    def getIqGateway(self, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "jabber:iq:gateway"
        query.addElement("desc", content="Enter XMPP name below")
        query.addElement("prompt", content="XMPP name")
        self.send(iq)

    def setIqGateway(self, el, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        prompt = xpath.XPathQuery(
             '/iq/query[@xmlns="jabber:iq:gateway"]/prompt').queryForString(el)
        if prompt == None:
            prompt = ''
        query = iq.addElement("query")
        query.attributes["xmlns"] = "jabber:iq:gateway"
        query.addElement("jid", content=self.quoteJID(prompt))
        self.send(iq)

    def getLast(self, fro, ID):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "jabber:iq:last"
        query.attributes["seconds"] = str(int(time.time()-self.startTime))
        self.send(iq)

    def getVersion(self, fro, ID):
        iq = Element((None,"iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "jabber:iq:version"
        query.addElement("name",
                content="J2J Transport (http://JRuDevels.org) Twisted-version")
        query.addElement("version", content = self.VERSION)
        self.send(iq)

    def getDiscoInfo(self, el, fro, ID, node):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "http://jabber.org/protocol/disco#info"
        if node:
            query.attributes["node"] = node
            if node == 'http://jabber.org/protocol/commands':
                identity = query.addElement("identity")
                identity.attributes["name"] = "Commands"
                identity.attributes["category"] = "automation"
                identity.attributes["type"] = "command-list"
            if node in self.adhoc.commands.keys():
                if self.adhoc.commands[node][3]:
                    uid = self.db.getIdByJid(fro.userhost())
                    if not uid:
                        self.sendError(el, etype="auth",
                                       condition="not-authorized")
                        return
                identity = query.addElement("identity")
                identity.attributes["name"] = self.adhoc.commands[node][0]
                identity.attributes["category"] = "automation"
                identity.attributes["type"] = "command-node"
                query.addElement("feature").attributes["var"] = \
                                    "http://jabber.org/protocol/commands"
                query.addElement("feature").attributes["var"] = "jabber:x:data"
            if (node.startswith("groster") and \
               self.clients.has_key(fro.full())) or \
               (node.startswith("users") \
                 and fro.userhost() in self.config.ADMINS):
                query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/disco#items"
                query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/disco#info"
        else:
            identity = query.addElement("identity")
            identity.attributes["name"] = "J2J: XMPP-Transport"
            identity.attributes["category"] = "gateway"
            identity.attributes["type"] = "XMPP"
            query.addElement("feature").attributes["var"] = "vcard-temp"
            query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/commands"
            query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/stats"
            query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/disco#items"
            query.addElement("feature").attributes["var"] = \
                                       "http://jabber.org/protocol/disco#info"
            query.addElement("feature").attributes["var"] = "jabber:iq:gateway"
            query.addElement("feature").attributes["var"] = \
                                       "jabber:iq:register"
            query.addElement("feature").attributes["var"] = "jabber:iq:last"
            query.addElement("feature").attributes["var"] = "jabber:iq:version"
        self.send(iq)

    def getDiscoItems(self, el, fro, ID, node):
        iq = Element((None, "iq"))
        iq.attributes["type"] = "result"
        iq.attributes["from"] = self.cJid
        iq.attributes["to"] = fro.full()
        if ID:
            iq.attributes["id"] = ID
        query = iq.addElement("query")
        query.attributes["xmlns"] = "http://jabber.org/protocol/disco#items"
        if node:
            query.attributes["node"] = node
        if node == None:
            utils.addDiscoItem(query,
                               self.cJid,
                               "Commands",
                               'http://jabber.org/protocol/commands')
            self.adhoc.getCommandsList(query)
            if fro.userhost() in self.config.ADMINS:
                utils.addDiscoItem(query,
                                   self.cJid,
                                   "Users",
                                   'users')
            if self.clients.has_key(fro.full()):
                utils.addDiscoItem(query,
                       self.quoteJID(self.clients[fro.full()].client_jid.host),
                       "Guest's server Discovery")
                utils.addDiscoItem(query,
                                   self.cJid,
                                   "Guest roster",
                                   "groster")
        elif node == "groster" and self.clients.has_key(fro.full()):
            groups = self.clients[fro.full()].roster.getGroups()
            for group in groups:
                utils.addDiscoItem(query,
                                   self.cJid,
                                   group,
                                   "groster/" + group)
        elif node == "users" and (fro.userhost() in self.config.ADMINS):
            utils.addDiscoItem(query,
                               self.cJid,
                               "Online users",
                               'users/online')
        elif node == "users/online" and (fro.userhost() in self.config.ADMINS):
            for user in self.clients.keys():
                utils.addDiscoItem(query, user)
        elif node.startswith("groster/") and self.clients.has_key(fro.full()):
            group = node[8:]
            contacts = self.clients[fro.full()].roster.getAllInGroup(group)
            for contact in contacts:
                utils.addDiscoItem(query,
                                   self.quoteJID(contact[0]),
                                   contact[1])
        elif node == "http://jabber.org/protocol/commands":
            self.adhoc.getCommandsList(query)
        elif node in self.adhoc.commands.keys():
            if self.adhoc.commands[node][3]:
                uid = self.db.getIdByJid(fro.userhost())
                if not uid:
                    self.sendError(el, etype="auth", 
                                   condition="not-authorized")
                    return
        self.send(iq)

    def sendIqResult(self, to, fro, ID, xmlns):
        el = Element((None,"iq"))
        el.attributes["to"] = to
        el.attributes["from"] = fro
        if ID:
            el.attributes["id"] = ID
            el.attributes["type"] = "result"
            self.send(el)

    def sendError(self, el, etype, condition, sender=None):
        fro = el.attributes['from']
        el.attributes['from'] = el.attributes['to']
        el.attributes['to'] = fro
        el.attributes['type'] = 'error'
        error = el.addElement("error")
        error.attributes['type'] = etype
        error.attributes['code'] = str(utils.errorCodeMap[condition])
        cond = error.addElement(condition)
        cond.attributes["xmlns"] = "urn:ietf:params:xml:ns:xmpp-stanzas"
        if sender is None:
            sender = self
        sender.send(el)

    def shuttingDown(self, signum, _):
        if self.shuttingDown:
            self.reactor.stop()
            return
        self.shuttingDown = True
        presence = Element((None, 'presence'))
        presence.attributes['type'] = 'unavailable'
        presence.attributes['to'] = self.cJid
        for cl in self.clients.values():
            presence.attributes['from'] = cl.host_jid.full()
            self.componentPresence(presence, cl.host_jid, 'unavailable')

        def x(ignored=False):
            self.reactor.stop()
        self.reactor.callLater(3, x, None)

    def quoteJID(self, ujid):
        if ujid == '' or ujid == None:
            return ''
        try:
            els = jid.parse(ujid)
        except:
            return self.cJid
        if els[0] == None:
            qjid = els[1]
        else:
            qjid = els[0] + "@" + els[1]
        qjid = qjid.replace('%','\\%')
        qjid = qjid.replace('@','%')
        qjid = qjid + '@' + self.cJid
        if ujid.find('/') != -1:
            qjid = qjid + '/' + els[2]
        return qjid

    def unquoteJID(self, qjid):
        if qjid == '' or qjid == None:
            return ''
        try:
            els = jid.parse(qjid)
        except:
            return self.cJid
        ujid = els[0]
        ujid = ujid.replace('%','@')
        ujid = ujid.replace('\\@','%')
        if qjid.find('/') != -1:
            ujid = ujid + '/' + els[2]
        return ujid


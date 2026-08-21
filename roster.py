# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the guest-side roster tracking.

from slixmpp.stanza import Iq, Presence
from slixmpp.stanza.roster import RosterItem

from utils import quoteJID

class Roster:
    def __init__(self, host):
        self.host = host
        self.items = {}

    def getGroups(self):
        groups = []
        alreadyUndefined = False
        for contact in self.items.keys():
            if self.items[contact][2] == [] and not alreadyUndefined:
                groups.append(u"Undefined")
                alreadyUndefined = True
            else:
                for group in self.items[contact][2]:
                    if not group in groups:
                        groups.append(group)
        return groups

    def getAllInGroup(self, group):
        if group == "Undefined":
            group = None
        all = []
        for contact in self.items.keys():
            if group:
                if group in self.items[contact][2]:
                    all.append([contact, self.items[contact][0]])
            elif self.items[contact][2] == []:
                all.append([contact, self.items[contact][0]])
        return all

    def updateFromClientRoster(self):
        items = {}
        for jid, item in self.host.client_roster.items():
            contact = str(jid)
            items[contact] = [item['name'], item['subscription'],
                              list(item['groups'])]
        self.items = items

    def removeItem(self, jid):
        if jid in self.items.keys():
            iq = self.host.Iq(stype='set')
            iq['roster']['items'] = [(jid, None, 'remove')]
            iq.send()
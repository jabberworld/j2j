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

    def getGroups(self, ungrouped="Undefined", exclude=None):
        """Group names across the roster. Contacts without any group are
        reported under the single pseudo-group *ungrouped*; bare JIDs in
        *exclude* (e.g. the guest account itself) are skipped."""
        skip = exclude or set()
        groups = []
        alreadyUngrouped = False
        for contact in self.items.keys():
            if contact in skip:
                continue
            if self.items[contact][2] == [] and not alreadyUngrouped:
                groups.append(ungrouped)
                alreadyUngrouped = True
            else:
                for group in self.items[contact][2]:
                    if not group in groups:
                        groups.append(group)
        return groups

    def getAllInGroup(self, group, ungrouped="Undefined", exclude=None):
        """(jid, name) pairs of every contact in *group*. The pseudo-group
        name *ungrouped* selects contacts without any group; bare JIDs in
        *exclude* are skipped."""
        skip = exclude or set()
        if group == ungrouped:
            group = None
        all = []
        for contact in self.items.keys():
            if contact in skip:
                continue
            if group:
                if group in self.items[contact][2]:
                    all.append([contact, self.items[contact][0]])
            elif self.items[contact][2] == []:
                all.append([contact, self.items[contact][0]])
        return all

    def updateFromClientRoster(self):
        items = {}
        for jid in self.host.client_roster.keys():
            item = self.host.client_roster[jid]
            contact = str(jid)
            items[contact] = [item['name'], item['subscription'],
                              list(item['groups'])]
        self.items = items

    def removeItem(self, jid):
        if jid in self.items.keys():
            iq = self.host.Iq(stype='set')
            iq['roster']['items'] = [(jid, None, 'remove')]
            iq.send()
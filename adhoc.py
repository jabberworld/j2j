# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the adhoc commands.

import time

import utils

class AdHoc:
    def __init__(self, component):
        self.commands = {
            "stat": ["Statistics", self.getStat, None, False],
            "options": ["Options", self.getOpts, self.setOpts, True],
            "replicate_vCard":
                ["Replicate host's vCard to guest's account",
                 self.getReplica, self.setReplica, True]}
        self.sid = 0
        self.vCardSids = {}

        self.component = component
        self.config = component.config

    def getSid(self):
        ret = time.strftime("%Y%m%dT%H%M%S",
                            time.localtime(time.time())) + \
              "-" + str(self.sid)
        self.sid += 1
        return ret

    def getCommandsList(self, query):
        for commandNode in self.commands:
            utils.addDiscoItem(query,
                               self.component.cJid,
                               self.commands[commandNode][0],
                               commandNode)

    def onCommand(self, el, fro, ID, node):
        node_el = getattr(el, 'xml', el)
        command_child = None
        for q in list(node_el):
            if utils.locname(q) == 'command':
                command_child = q
        if command_child is None:
            return "cancel", "item-not-found"
        sid = command_child.get('sessionid')
        action = command_child.get('action') or 'execute'
        if node not in self.commands:
            return "cancel", "item-not-found"

        iq = utils.addsub(None, "iq", utils.COMPONENT_NS)
        iq.set("to", fro.full)
        iq.set("from", self.component.cJid)
        iq.set("id", ID)
        iq.set("type", "result")

        if action == 'execute' and sid is None:
            self.commands[node][1](iq, fro, ID)
            return None, None

        if action == 'cancel':
            utils.createCommand(iq, node, "canceled", sid)
            self.component.send(utils.tostring(iq))
            return None, None

        if action in ('complete', 'execute') and sid is not None and \
           self.commands[node][2] is not None:
            self.commands[node][2](el, iq, sid, fro, ID)
            return None, None

        return "cancel", "bad-request"

    def getReplica(self, iq, fro, ID):
        if fro.full not in self.component.clients:
            command = utils.createCommand(iq, "stat", "completed",
                                          self.getSid())
            form = utils.createForm(command, "result")
            utils.addTitle(form, "Execution error")
            utils.addLabel(form, "Please log in first.")
            self.component.send(utils.tostring(iq))
            return
        command = utils.createCommand(iq, "replicate_vCard",
                                      "executing", self.getSid())
        form = utils.createForm(command, "form")
        utils.addTitle(form, "vCard replication")
        utils.addLabel(
            form,
            "Are you sure want to replicate your host's vCard to "
            "your guest's account?")
        utils.addCheckBox(form, "commit_cb", "Yes, do it", False)
        self.component.send(utils.tostring(iq))

    def setReplica(self, el, iq, sid, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return
        committed = utils.xdataValue(el, 'commit_cb')
        if committed == "0" or fro.full not in self.component.clients:
            command = utils.createCommand(iq, "replicate_vCard",
                                          "completed", sid)
            form = utils.createForm(command, "result")
            utils.addTitle(form, "Execution canceled")
            utils.addLabel(form, "Replication cancelled")
            self.component.send(utils.tostring(iq))
            return
        vex = utils.addsub(None, "iq", utils.COMPONENT_NS)
        vex.set("to", fro.bare)
        vex.set("from", self.component.cJid)
        vex.set("id", sid)
        vex.set("type", "get")
        utils.addsub(vex, "vCard", utils.VCARD_NS)
        self.component.send(utils.tostring(vex))
        self.vCardSids[sid] = (fro, ID)

    def getStat(self, iq, fro, ID):
        command = utils.createCommand(iq, "stat", "completed",
                                      self.getSid())
        form = utils.createForm(command, "result")
        utils.addTitle(form, "J2J Statistics")
        utils.addLabel(form, "J2J Statistics")
        utils.addLabel(form, "Online Users: " +
                       str(len(self.component.clients)))
        utils.addLabel(form, "Total Users: " +
                       str(self.component.db.getCount("users")))
        utils.addLabel(form, "Version: " + self.component.VERSION)
        upInSecs = int(time.time() - self.component.startTime)
        upInDays = int(upInSecs / (3600 * 24))
        upInHours = int((upInSecs - upInDays * 3600 * 24) / 3600)
        upInMinutes = int((upInSecs - upInDays * 3600 * 24 -
                           upInHours * 3600) / 60)
        upInSecs = int(upInSecs - upInDays * 3600 * 24 -
                       upInHours * 3600 - upInMinutes * 60)
        utils.addLabel(form, "Uptime: %d days %d hours %d minutes "
                             "%d seconds" % (upInDays, upInHours,
                                             upInMinutes, upInSecs))
        self.component.send(utils.tostring(iq))

    def getOpts(self, iq, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return
        opts = self.component.db.getOptsById(uid)
        command = utils.createCommand(iq, "options", "executing",
                                      self.getSid())
        form = utils.createForm(command, "form")
        utils.addTitle(form, "J2J Options and Settings")
        utils.addCheckBox(form, "onlyRoster",
                          "Receive messages only from contacts from "
                          "Guest roster", opts[2])
        utils.addLabel(form, "Auto Reply Settings")
        utils.addCheckBox(form, "autoReplyEnabled",
                          "Enable Auto Reply for ALL guest contacts",
                          opts[3])
        utils.addCheckBox(form, "autoReplyButForward",
                          "Always forward messages to me", opts[1])
        utils.addMemo(form, "replyText",
                      "Text for Auto Reply (1000 chars max)", opts[0])
        self.component.send(utils.tostring(iq))

    def setOpts(self, el, iq, sid, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return
        opts = self.component.db.getOptsById(uid)
        command = utils.createCommand(iq, "options", "completed", sid)
        onlyRoster = utils.xdataValue(el, 'onlyRoster')
        if onlyRoster:
            opts[2] = utils.strToBool(onlyRoster)
        autoReplyEnabled = utils.xdataValue(el, 'autoReplyEnabled')
        if autoReplyEnabled:
            opts[3] = utils.strToBool(autoReplyEnabled)
        autoReplyButForward = utils.xdataValue(el, 'autoReplyButForward')
        if autoReplyButForward:
            opts[1] = utils.strToBool(autoReplyButForward)
        replyText = utils.xdataValueList(el, 'replyText')
        if replyText:
            rT = "\n".join(replyText)
            rT = rT[:1000]
            opts[0] = rT
        self.component.db.execute(
            "UPDATE users_options SET onlyroster=?,"
            "autoreplyenabled=?,autoreplybutforward=?,replytext=? "
            "WHERE user_id=?",
            (int(opts[2]), int(opts[3]), int(opts[1]), opts[0],
             str(uid)))
        self.component.db.commit()
        utils.createNote(command, "info", "Options were updated")
        self.component.send(utils.tostring(iq))
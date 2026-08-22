# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port of the adhoc commands.

import time

import i18n
import utils

class AdHoc:
    # Menu entries of the administration command, in display order.
    ADMIN_ACTIONS = ("setlang", "setmode", "setgroup",
                     "restart", "stop", "announce")

    # Roster import mechanisms offered to the admin (config values).
    IMPORT_MODES = ("off", "subscribe", "rosterx", "auto")
    MODE_KEYS = {"off": "import_opt_off",
                 "subscribe": "import_opt_subscribe",
                 "rosterx": "import_opt_rosterx",
                 "auto": "import_opt_auto"}

    def __init__(self, component):
        # Each entry: [i18n key, stage-1 handler, stage-2 handler,
        # hidden_for_unregistered, admin_only]. The i18n key is
        # resolved against the requester's language at render time.
        self.commands = {
            "register": ["cmd_register", self.getRegisterAdhoc,
                         self.setRegisterAdhoc, False, False],
            "stat": ["cmd_stat", self.getStat, None, False, False],
            "options": ["cmd_options", self.getOpts, self.setOpts,
                        True, False],
            "replicate_vCard":
                ["cmd_replicate_vcard", self.getReplica,
                 self.setReplica, True, False],
            "admin": ["cmd_admin", self.getAdmin, self.setAdmin,
                      False, True]}
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

    def getCommandsList(self, query, lang, fro):
        """Populate a disco#items query with the commands visible to
        this requester: administration only for admins, everything
        else also for unregistered users except commands that cannot
        do anything without a registered account."""
        registered = \
            self.component.db.getIdByJid(fro.bare) is not None
        is_admin = fro.bare in self.config.ADMINS
        for commandNode in self.commands:
            cmd = self.commands[commandNode]
            if cmd[4] and not is_admin:
                continue
            if cmd[3] and not registered:
                continue
            utils.addDiscoItem(query,
                               self.component.cJid,
                               i18n.t(lang, cmd[0]),
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
        if self.commands[node][4] and \
           fro.bare not in self.config.ADMINS:
            return "cancel", "not-authorized"
        if self.commands[node][3] and \
           self.component.db.getIdByJid(fro.bare) is None:
            # Commands hidden from the disco list are also refused
            # when addressed directly by an unregistered user.
            return "cancel", "registration-required"

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

    # ---- registration ----

    def getRegisterAdhoc(self, iq, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        uid, data = self.component.registerContext(fro)

        def send_form(rosterx_supported):
            command = utils.createCommand(iq, "register",
                                          "executing", self.getSid())
            mode_default = \
                self.component.defaultImportMode(self.component.config,
                                                 rosterx_supported)
            self.component.buildRegisterForm(command, lang, uid, data,
                                             mode_default=mode_default)
            self.component.send(utils.tostring(iq))

        if uid is not None:
            send_form(False)
        else:
            self.component.probeRosterxSupport(fro.full, send_form)

    def setRegisterAdhoc(self, el, iq, sid, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        ok, _err, created = self.component.submitRegistration(el, fro)
        command = utils.createCommand(iq, "register", "completed", sid)
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "reg_title"))
        if ok:
            utils.addLabel(form, i18n.t(
                lang,
                "note_register_done" if created
                else "note_register_updated"))
        else:
            utils.addLabel(form,
                           i18n.t(lang, "reg_error_invalid_data"))
        self.component.send(utils.tostring(iq))

    # ---- vCard replication ----

    def getReplica(self, iq, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        if fro.full not in self.component.clients:
            command = utils.createCommand(iq, "stat", "completed",
                                          self.getSid())
            form = utils.createForm(command, "result")
            utils.addTitle(form, i18n.t(lang, "replica_err_title"))
            utils.addLabel(form, i18n.t(lang, "replica_need_login"))
            self.component.send(utils.tostring(iq))
            return
        command = utils.createCommand(iq, "replicate_vCard",
                                      "executing", self.getSid())
        form = utils.createForm(command, "form")
        utils.addTitle(form, i18n.t(lang, "replica_title"))
        utils.addLabel(form, i18n.t(lang, "replica_confirm"))
        utils.addCheckBox(form, "commit_cb",
                          i18n.t(lang, "replica_yes"), False)
        self.component.send(utils.tostring(iq))

    def setReplica(self, el, iq, sid, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return
        lang = self.component.getUserLang(fro.bare)
        committed = utils.xdataValue(el, 'commit_cb')
        if committed == "0" or fro.full not in self.component.clients:
            command = utils.createCommand(iq, "replicate_vCard",
                                          "completed", sid)
            form = utils.createForm(command, "result")
            utils.addTitle(form,
                           i18n.t(lang, "replica_cancel_title"))
            utils.addLabel(form, i18n.t(lang, "replica_cancelled"))
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

    # ---- statistics ----

    def getStat(self, iq, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        command = utils.createCommand(iq, "stat", "completed",
                                      self.getSid())
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "stat_title"))
        utils.addLabel(form, i18n.t(lang, "stat_title"))
        utils.addLabel(form,
                       i18n.t(lang, "stat_online_users") %
                       len(self.component.clients))
        utils.addLabel(form,
                       i18n.t(lang, "stat_total_users") %
                       self.component.db.getCount("users"))
        utils.addLabel(form,
                       i18n.t(lang, "stat_version") %
                       self.component.VERSION)
        upInSecs = int(time.time() - self.component.startTime)
        upInDays = int(upInSecs / (3600 * 24))
        upInHours = int((upInSecs - upInDays * 3600 * 24) / 3600)
        upInMinutes = int((upInSecs - upInDays * 3600 * 24 -
                           upInHours * 3600) / 60)
        upInSecs = int(upInSecs - upInDays * 3600 * 24 -
                       upInHours * 3600 - upInMinutes * 60)
        utils.addLabel(form,
                       i18n.t(lang, "stat_uptime") %
                       (upInDays, upInHours, upInMinutes, upInSecs))
        self.component.send(utils.tostring(iq))

    # ---- user options ----

    def getOpts(self, iq, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return  # unreachable via onCommand (gated), safety net
        opts = self.component.db.getOptsById(uid)
        lang = self.component.effectiveLang(opts[4])
        command = utils.createCommand(iq, "options", "executing",
                                      self.getSid())
        form = utils.createForm(command, "form")
        utils.addTitle(form, i18n.t(lang, "opts_title"))
        utils.addCheckBox(form, "onlyRoster",
                          i18n.t(lang, "opts_only_roster"), opts[2])
        utils.addLabel(form, i18n.t(lang, "opts_autoreply_header"))
        utils.addCheckBox(form, "autoReplyEnabled",
                          i18n.t(lang, "opts_autoreply_enabled"),
                          opts[3])
        utils.addCheckBox(form, "autoReplyButForward",
                          i18n.t(lang, "opts_autoreply_forward"),
                          opts[1])
        utils.addMemo(form, "replyText",
                      i18n.t(lang, "opts_reply_text"), opts[0])
        utils.addListSingle(form, "language",
                            i18n.t(lang, "field_language"),
                            lang, i18n.options())
        utils.addCheckBox(form, "disableAccount",
                          i18n.t(lang, "opts_disable_account"),
                          bool(opts[5]))
        utils.addCheckBox(form, "remove_from_roster",
                          i18n.t(lang, "field_remove_from_roster"),
                          bool(opts[6]))
        self.component.send(utils.tostring(iq))

    def setOpts(self, el, iq, sid, fro, ID):
        uid = self.component.db.getIdByJid(fro.bare)
        if not uid:
            return  # unreachable via onCommand (gated), safety net
        opts = self.component.db.getOptsById(uid)
        lang = self.component.effectiveLang(opts[4])
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
        # Only touch the stored language when the form actually
        # carried the field (older cached forms may omit it).
        lang_submitted = (utils.xdataValue(el, 'language') or '').strip()
        if lang_submitted:
            opts[4] = i18n.normalize(lang_submitted)
        self.component.db.execute(
            "UPDATE users_options SET onlyroster=?,"
            "autoreplyenabled=?,autoreplybutforward=?,replytext=?,"
            "language=? WHERE user_id=?",
            (int(opts[2]), int(opts[3]), int(opts[1]), opts[0],
             opts[4], str(uid)))
        self.component.db.commit()
        note_key = "note_options_updated"
        disabled_submitted = utils.xdataValue(el, 'disableAccount')
        if disabled_submitted:
            want_disabled = utils.strToBool(disabled_submitted)
            if bool(opts[5]) != want_disabled:
                self.component.db.setDisabled(uid, want_disabled)
                if want_disabled:
                    self.component.disconnectGuestSessions(fro.bare)
                    note_key = "note_account_disabled"
                else:
                    note_key = "note_account_enabled"
                    pres = self.component.make_presence(
                        ptype="available", pto=self.component.cJid,
                        pfrom=fro.full)
                    self.component.connectGuestSession(fro, uid, pres)
        # Only touch the guest-roster cleanup flag when the form
        # actually carried the field (older cached forms omit it).
        # Applies to new guest sessions after reconnect.
        rfr_submitted = utils.xdataValue(el, 'remove_from_roster')
        if rfr_submitted is not None:
            self.component.db.setRemoveFromGuestRoster(
                uid, utils.strToBool(rfr_submitted))
        utils.createNote(command, "info", i18n.t(lang, note_key))
        self.component.send(utils.tostring(iq))

    # ---- administration ----

    def getAdmin(self, iq, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        command = utils.createCommand(iq, "admin", "executing",
                                      self.getSid())
        form = utils.createForm(command, "form")
        utils.addTitle(form, i18n.t(lang, "admin_title"))
        actions = [(action,
                    i18n.t(lang, "admin_act_" + action))
                   for action in self.ADMIN_ACTIONS]
        utils.addListSingle(form, "action",
                            i18n.t(lang, "admin_action_label"),
                            self.ADMIN_ACTIONS[0], actions)
        self.component.send(utils.tostring(iq))

    def setAdmin(self, el, iq, sid, fro, ID):
        lang = self.component.getUserLang(fro.bare)
        action = utils.xdataValue(el, 'action')
        if action == "setlang":
            self.adminSetLang(el, iq, sid, fro, lang)
        elif action == "setmode":
            self.adminSetMode(el, iq, sid, fro, lang)
        elif action == "setgroup":
            self.adminSetGroup(el, iq, sid, fro, lang)
        elif action in ("restart", "stop"):
            self.adminPower(action, el, iq, sid, fro, lang)
        elif action == "announce":
            self.adminAnnounce(el, iq, sid, fro, lang)
        else:
            # Unknown or missing action: show the menu again.
            self.getAdmin(iq, fro, ID)

    def adminSetLang(self, el, iq, sid, fro, lang):
        chosen = (utils.xdataValue(el, 'language') or '').strip()
        if not chosen:
            command = utils.createCommand(iq, "admin", "executing",
                                          sid)
            form = utils.createForm(command, "form")
            utils.addTitle(form, i18n.t(lang, "setlang_title"))
            utils.addListSingle(form, "language",
                                i18n.t(lang, "field_language"),
                                self.component.config.DEFAULT_LANGUAGE,
                                i18n.options())
            utils.addHidden(form, "action", "setlang")
            self.component.send(utils.tostring(iq))
            return
        changed = self.component.config.setDefaultLanguage(chosen)
        command = utils.createCommand(iq, "admin", "completed", sid)
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "setlang_title"))
        utils.addLabel(form,
                       i18n.t(lang, "note_setlang_done") %
                       i18n.normalize(chosen))
        self.component.send(utils.tostring(iq))
        if not changed:
            self.component.debug.logger.warning(
                "Config file path unknown; default language %r "
                "applied in memory only", i18n.normalize(chosen))

    def adminSetMode(self, el, iq, sid, fro, lang):
        chosen = (utils.xdataValue(el, 'import_mode') or
                  '').strip().lower()
        if chosen not in self.IMPORT_MODES:
            command = utils.createCommand(iq, "admin", "executing",
                                          sid)
            form = utils.createForm(command, "form")
            utils.addTitle(form, i18n.t(lang, "admin_act_setmode"))
            modes = [(mode,
                      i18n.t(lang, self.MODE_KEYS[mode]))
                     for mode in self.IMPORT_MODES]
            utils.addListSingle(form, "import_mode",
                                i18n.t(lang, "field_import_mode"),
                                self.component.config.IMPORT_MODE,
                                modes)
            utils.addHidden(form, "action", "setmode")
            self.component.send(utils.tostring(iq))
            return
        changed = self.component.config.setImportMode(chosen)
        command = utils.createCommand(iq, "admin", "completed", sid)
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "admin_act_setmode"))
        utils.addLabel(form, i18n.t(lang, "note_setmode_done") % chosen)
        self.component.send(utils.tostring(iq))
        if not changed:
            self.component.debug.logger.warning(
                "Config file path unknown; import mode %r "
                "applied in memory only", chosen)

    def adminSetGroup(self, el, iq, sid, fro, lang):
        chosen = (utils.xdataValue(el, 'import_group') or '').strip()
        if not chosen:
            command = utils.createCommand(iq, "admin", "executing",
                                          sid)
            form = utils.createForm(command, "form")
            utils.addTitle(form, i18n.t(lang, "admin_act_setgroup"))
            utils.addTextBox(
                form, "import_group",
                i18n.t(lang, "field_import_group"),
                self.component.config.ROSTER_GROUP_NAME)
            utils.addHidden(form, "action", "setgroup")
            self.component.send(utils.tostring(iq))
            return
        changed = self.component.config.setRosterGroupName(chosen)
        command = utils.createCommand(iq, "admin", "completed", sid)
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "admin_act_setgroup"))
        utils.addLabel(form, i18n.t(lang, "note_setgroup_done") %
                       self.component.config.ROSTER_GROUP_NAME)
        self.component.send(utils.tostring(iq))
        if not changed:
            self.component.debug.logger.warning(
                "Config file path unknown; roster group name %r "
                "applied in memory only",
                self.component.config.ROSTER_GROUP_NAME)

    def adminPower(self, action, el, iq, sid, fro, lang):
        act_key = "admin_act_" + action
        confirmed = utils.xdataValue(el, 'confirm')
        if confirmed == '':
            command = utils.createCommand(iq, "admin", "executing",
                                          sid)
            form = utils.createForm(command, "form")
            utils.addTitle(form, i18n.t(lang, act_key))
            utils.addLabel(form, i18n.t(lang, act_key))
            utils.addCheckBox(form, "confirm",
                              i18n.t(lang, "admin_confirm_label"),
                              False)
            utils.addHidden(form, "action", action)
            self.component.send(utils.tostring(iq))
            return
        command = utils.createCommand(iq, "admin", "completed", sid)
        form = utils.createForm(command, "result")
        if not utils.strToBool(confirmed):
            utils.addTitle(form, i18n.t(lang, "replica_cancel_title"))
            utils.addLabel(form,
                           i18n.t(lang, "note_action_cancelled"))
            self.component.send(utils.tostring(iq))
            return
        utils.addTitle(form, i18n.t(lang, act_key))
        utils.addLabel(form, i18n.t(
            lang, "note_restart_done" if action == "restart"
            else "note_stop_done"))
        self.component.send(utils.tostring(iq))
        # Let the completion stanza reach the server before tearing
        # the process down.
        self.component.loop.call_later(
            1.5, self.component.requestShutdown, action == "restart")

    def adminAnnounce(self, el, iq, sid, fro, lang):
        text = "\n".join(utils.xdataValueList(el, 'text')).strip()
        if not text:
            command = utils.createCommand(iq, "admin", "executing",
                                          sid)
            form = utils.createForm(command, "form")
            utils.addTitle(form, i18n.t(lang, "announce_title"))
            utils.addMemo(form, "text",
                          i18n.t(lang, "announce_text_label"), '')
            utils.addHidden(form, "action", "announce")
            self.component.send(utils.tostring(iq))
            return
        count = 0
        for jid in self.component.db.activeUserJids():
            msg = self.component.make_message(mto=jid,
                                              mfrom=self.component.cJid,
                                              mtype="headline")
            msg['body'] = text
            msg.send()
            count += 1
        command = utils.createCommand(iq, "admin", "completed", sid)
        form = utils.createForm(command, "result")
        utils.addTitle(form, i18n.t(lang, "announce_title"))
        utils.addLabel(form,
                       i18n.t(lang, "note_announce_sent") % count)
        self.component.send(utils.tostring(iq))

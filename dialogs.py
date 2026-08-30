# Part of J2J (http://JRuDevels.org)

import uuid

from slixmpp.jid import InvalidJID, JID

import i18n
import utils


class MessageDialogs:
    """The line-oriented chat interface exposed by the transport."""

    def __init__(self, component):
        self.component = component
        self.dialogs = {}
        self.languages = {}
        self.text_vcard_sids = {}

    def _text(self, fro, key, *args):
        msg = self.component.make_message(mto=fro.full, mfrom=self.component.cJid,
                                          mtype="chat")
        lang = self.languages.get(fro.bare, self.component.getUserLang(fro.bare))
        msg['body'] = i18n.t(lang, key) % args
        msg.send()

    def _menu(self, fro):
        registered = self.component.db.getIdByJid(fro.bare) is not None
        self._text(fro, "msg_welcome")
        self._text(fro, "msg_menu_registered" if registered else "msg_menu_guest")

    def handle(self, fro, body):
        sender = fro.bare
        text = str(body).strip()
        if not text:
            self._menu(fro)
            return
        dialog = self.dialogs.get(sender)
        if dialog:
            if text == "0":
                del self.dialogs[sender]
                self._text(fro, "msg_exit")
                self._menu(fro)
                return
            self._dialog(fro, dialog, text)
            return
        command = text.lower().lstrip('/').split(None, 1)[0]
        registered = self.component.db.getIdByJid(sender) is not None
        aliases = {"1": "mod", "2": "lang", "3": "on", "4": "off",
                   "5": "del", "6": "vcard", "7": "arepl", "8": "trans",
                   "9": "help", "h": "help", "?": "help"}
        if not registered:
            aliases = {"1": "reg", "2": "lang", "3": "help",
                       "h": "help", "?": "help"}
        command = aliases.get(command, command)
        if command in ("help", "menu"):
            self._menu(fro)
        elif command in ("reg", "mod") and (not registered or command == "mod"):
            self._beginRegistration(fro)
        elif command == "lang":
            self.dialogs[sender] = {"kind": "lang"}
            self._languageMenu(fro)
        elif registered and command in ("on", "off"):
            self._accountSwitch(fro, command == "on")
        elif registered and command in ("del", "vcard"):
            kind = "delete" if command == "del" else "vcard"
            self.dialogs[sender] = {"kind": kind}
            self._confirmMenu(fro, "msg_delete_confirm" if kind == "delete"
                              else "msg_vcard_confirm")
        elif registered and command == "arepl":
            self._beginAutoreply(fro)
        elif registered and command == "trans":
            self._beginTrans(fro)
        else:
            self._text(fro, "msg_unknown")
            self._menu(fro)

    def _dialog(self, fro, dialog, text):
        kind = dialog["kind"]
        if kind == "lang":
            try:
                chosen = i18n.options()[int(text) - 1][0]
            except (ValueError, IndexError):
                self._text(fro, "msg_lang_invalid")
                self._languageMenu(fro)
                return
            uid = self.component.db.getIdByJid(fro.bare)
            if uid:
                self.component.db.setLangById(uid, chosen)
                self.component.db.commit()
            else:
                self.languages[fro.bare] = chosen
            del self.dialogs[fro.bare]
            self._text(fro, "msg_lang_done", i18n.LANGUAGES[chosen])
            self._menu(fro)
            return
        if kind in ("delete", "vcard"):
            if text != "1":
                self._text(fro, "msg_invalid_item")
                self._confirmMenu(fro, "msg_delete_confirm" if kind == "delete" else "msg_vcard_confirm")
                return
            del self.dialogs[fro.bare]
            if kind == "delete":
                self.component.deleteAccount(fro)
                self._text(fro, "msg_deleted")
                self._menu(fro)
            else:
                self._requestVcard(fro)
            return
        if kind == "registration":
            self._registrationStep(fro, dialog, text)
            return
        if kind == "autoreply":
            if dialog.get("step") == "text":
                if len(text) > 1000:
                    self._text(fro, "msg_arepl_invalid")
                    dialog["step"] = "menu"
                else:
                    dialog["replytext"] = text
                    uid = self.component.db.getIdByJid(fro.bare)
                    self.component.db.execute("UPDATE users_options SET replytext=? WHERE user_id=?", (text, str(uid)))
                    self.component.db.commit()
                    dialog["step"] = "menu"
                self._optionsMenu(fro, dialog)
                return
            if text.isdigit() and int(text) in (1, 2):
                name = "enabled" if text == "1" else "forward"
                dialog[name] = not dialog[name]
                uid = self.component.db.getIdByJid(fro.bare)
                self.component.db.execute("UPDATE users_options SET autoreplyenabled=?,autoreplybutforward=? WHERE user_id=?", (int(dialog["enabled"]), int(dialog["forward"]), str(uid)))
                self.component.db.commit()
                self._optionsMenu(fro, dialog)
            elif text == "3":
                dialog["step"] = "text"
                self._text(fro, "msg_arepl_text")
            elif text == "0":
                del self.dialogs[fro.bare]
                self._text(fro, "msg_exit")
                self._menu(fro)
            else:
                self._text(fro, "msg_invalid_item")
                self._optionsMenu(fro, dialog)
            return
        if kind == "trans":
            if text == "0":
                uid = self.component.db.getIdByJid(fro.bare)
                if uid:
                    self.component.db.setRemoveFromGuestRoster(uid, dialog["remove"])
                    self.component.db.execute("UPDATE users_options SET notify_typing=?,notify_activity=?,notify_receipts=?,rostersync=? WHERE user_id=?", (int(dialog["typing"]), int(dialog["activity"]), int(dialog["receipts"]), int(dialog["rostersync"]), str(uid)))
                    self.component.db.commit()
                del self.dialogs[fro.bare]
                self._text(fro, "msg_exit")
                self._menu(fro)
                return
            try:
                option = int(text)
            except ValueError:
                option = 0
            if option not in range(1, 7):
                self._text(fro, "msg_invalid_item")
                self._optionsMenu(fro, dialog)
                return
            name = ("onlyroster", "remove", "rostersync", "typing",
                    "activity", "receipts")[option - 1]
            dialog[name] = not dialog[name]
            uid = self.component.db.getIdByJid(fro.bare)
            if uid:
                if name == "remove":
                    self.component.db.setRemoveFromGuestRoster(uid,
                                                               dialog[name])
                else:
                    column = {"onlyroster": "onlyroster",
                              "rostersync": "rostersync",
                              "typing": "notify_typing",
                              "activity": "notify_activity",
                              "receipts": "notify_receipts"}[name]
                    self.component.db.execute(
                        "UPDATE users_options SET %s=? WHERE user_id=?" %
                        column, (int(dialog[name]), str(uid)))
                self.component.db.commit()
            self._optionsMenu(fro, dialog)
            return

    def _accountSwitch(self, fro, enabled):
        db = self.component.db
        uid = db.getIdByJid(fro.bare)
        db.setDisabled(uid, not enabled)
        db.commit()
        if enabled:
            self._text(fro, "msg_account_on")
            if fro.full not in self.component.clients:
                presence = self.component.make_presence(ptype="available", pto=self.component.cJid, pfrom=fro.full)
                self.component.connectGuestSession(fro, uid, presence)
        else:
            self.component.disconnectGuestSessions(fro.bare)
            self._text(fro, "msg_account_off")

    def _beginAutoreply(self, fro):
        opts = self.component.db.getOptsById(self.component.db.getIdByJid(fro.bare))
        self.dialogs[fro.bare] = {"kind": "autoreply", "step": "menu", "enabled": bool(opts[3]), "forward": bool(opts[1]), "replytext": opts[0] or ""}
        self._optionsMenu(fro, self.dialogs[fro.bare])

    def _beginTrans(self, fro):
        opts = self.component.db.getOptsById(self.component.db.getIdByJid(fro.bare))
        self.dialogs[fro.bare] = {"kind": "trans",
                                  "onlyroster": bool(opts[2]),
                                  "remove": bool(opts[6]),
                                  "rostersync": bool(opts[10]),
                                  "typing": bool(opts[7]),
                                  "activity": bool(opts[8]),
                                  "receipts": bool(opts[9])}
        self._optionsMenu(fro, self.dialogs[fro.bare])

    def _optionsMenu(self, fro, dialog):
        lang = self.languages.get(fro.bare, self.component.getUserLang(fro.bare))
        mark = lambda value: "[x]" if value else "[ ]"
        if dialog["kind"] == "autoreply":
            lines = ["1. %s %s" % (mark(dialog["enabled"]), i18n.t(lang, "opts_autoreply_enabled")), "2. %s %s" % (mark(dialog["forward"]), i18n.t(lang, "opts_autoreply_forward")), "3. %s: %s" % (i18n.t(lang, "opts_reply_text"), dialog["replytext"]), "0. " + i18n.t(lang, "msg_back")]
        else:
            labels = ("opts_only_roster", "field_remove_from_roster",
                      "opts_rostersync", "opts_typing", "opts_chatstates",
                      "opts_receipts")
            names = ("onlyroster", "remove", "rostersync", "typing",
                     "activity", "receipts")
            lines = ["%d. %s %s" % (i, mark(dialog[n]), i18n.t(lang, key)) for i, (n, key) in enumerate(zip(names, labels), 1)]
            lines.append("0. " + i18n.t(lang, "msg_back"))
        self._text(fro, "msg_options_menu", "\n".join(lines))

    def _beginRegistration(self, fro):
        uid, data = self.component.registerContext(fro)
        self.dialogs[fro.bare] = {"kind": "registration", "step": "menu", "uid": uid, "fields": {"jid": ((data[0] + "@" + data[2]) if uid else ""), "password": data[1] or "", "domain": data[3] or "", "port": str(data[4] or 5222), "import_roster": str(data[5] if data[5] else 0), "import_group": data[7] or "", "language": self.languages.get(fro.bare, self.component.getUserLang(fro.bare))}}
        self._registrationMenu(fro, self.dialogs[fro.bare])

    def _registrationMenu(self, fro, dialog):
        lang = self.languages.get(fro.bare, self.component.getUserLang(fro.bare)); fields = dialog["fields"]
        labels = ("field_jid", "field_password", "field_domain", "field_port", "field_import_mode", "field_import_group", "field_language")
        values = (fields["jid"], "********" if fields["password"] else "", fields["domain"], fields["port"], i18n.t(lang, ("import_opt_off", "import_opt_subscribe", "import_opt_rosterx")[int(fields["import_roster"])]), fields["import_group"], i18n.LANGUAGES.get(fields["language"], fields["language"]))
        lines = ["%d. %s (%s)" % (i, i18n.t(lang, label), value) for i, (label, value) in enumerate(zip(labels, values), 1)] + ["", "8. " + i18n.t(lang, "msg_confirm"), "", "0. " + i18n.t(lang, "msg_back")]
        self._text(fro, "msg_reg_menu", "\n".join(lines))

    def _registrationChoices(self, fro, step):
        lang = self.languages.get(fro.bare, self.component.getUserLang(fro.bare))
        if step == "import":
            keys = ("import_opt_off", "import_opt_subscribe", "import_opt_rosterx")
            lines = ["%d. %s" % (i, i18n.t(lang, key)) for i, key in enumerate(keys, 1)]
        else:
            lines = ["%d. %s" % (i, name) for i, (_code, name) in enumerate(i18n.options(), 1)]
        self._text(fro, "msg_reg_choices", "\n".join(lines))

    def _registrationStep(self, fro, dialog, text):
        fields = dialog["fields"]
        if dialog["step"] == "menu":
            if text == "0":
                del self.dialogs[fro.bare]; self._text(fro, "msg_exit"); self._menu(fro); return
            try: choice = int(text)
            except ValueError: choice = 0
            if choice == 8:
                self._submitRegistration(fro, dialog)
                return
            if choice not in range(1, 8): self._text(fro, "msg_invalid_item"); self._registrationMenu(fro, dialog); return
            dialog["step"] = ("jid", "password", "domain", "port", "import", "group", "language")[choice - 1]
            self._text(fro, {"jid":"msg_reg_jid", "password":"msg_reg_password", "domain":"msg_reg_domain", "port":"msg_reg_port", "import":"msg_reg_import", "group":"msg_reg_group", "language":"msg_reg_language"}[dialog["step"]])
            if dialog["step"] in ("import", "language"): self._registrationChoices(fro, dialog["step"])
            return
        step = dialog["step"]
        if step in ("import", "language"):
            try: choice = int(text)
            except ValueError: choice = 0
            if step == "import":
                if choice not in (1, 2, 3): self._text(fro, "msg_invalid_item"); self._registrationChoices(fro, step); return
                fields["import_roster"] = str(choice - 1)
            else:
                options = i18n.options()
                if choice not in range(1, len(options) + 1): self._text(fro, "msg_invalid_item"); self._registrationChoices(fro, step); return
                fields["language"] = options[choice - 1][0]
            dialog["step"] = "menu"; self._registrationMenu(fro, dialog); return
        valid = True
        if step == "jid":
            try: candidate = JID(text); valid = text.count("@") == 1 and bool(candidate.user and candidate.server) and not candidate.resource
            except InvalidJID: valid = False
            value = text
        elif step == "password": valid = bool(text) and len(text) <= 256 and "\n" not in text and "\r" not in text; value = text
        elif step == "domain":
            try: JID("user@" + text); valid = bool(text) and not any(ch.isspace() for ch in text)
            except InvalidJID: valid = False
            value = text
        elif step == "group": valid = len(text) <= 128 and "\n" not in text and "\r" not in text; value = text
        elif step == "port":
            try: value = str(int(text)); valid = 1 <= int(text) <= 65535
            except ValueError: value = text; valid = False
        else:
            answer = text.lower()
            if answer not in ("y", "yes", "да", "так", "n", "no", "нет", "ні"): self._text(fro, "msg_yes_no"); return
            if answer not in ("y", "yes", "да", "так"):
                del self.dialogs[fro.bare]; self._text(fro, "msg_cancelled"); self._menu(fro); return
            query = utils.addsub(None, "query", "jabber:iq:register"); xdata = utils.createForm(query, "submit")
            for name, val in fields.items(): utils.addsub(utils.addsub(xdata, "field", utils.X_DATA_NS, {"var": name}), "value", utils.X_DATA_NS, text=val)
            self._submitRegistration(fro, dialog, query)
            return
        if not valid: dialog["step"] = "menu"; self._text(fro, "msg_reg_invalid"); self._registrationMenu(fro, dialog); return
        fields["jid" if step == "jid" else {"password":"password", "domain":"domain", "group":"import_group", "port":"port"}[step]] = value
        dialog["step"] = "menu"; self._registrationMenu(fro, dialog)

    def _submitRegistration(self, fro, dialog, query=None):
        if query is None:
            query = utils.addsub(None, "query", "jabber:iq:register")
            xdata = utils.createForm(query, "submit")
            for name, value in dialog["fields"].items():
                field = utils.addsub(xdata, "field", utils.X_DATA_NS, {"var": name})
                utils.addsub(field, "value", utils.X_DATA_NS, text=value)
        ok, _error, _created = self.component.submitRegistration(query, fro)
        del self.dialogs[fro.bare]
        self.languages.pop(fro.bare, None)
        self._text(fro, "msg_register_done" if ok else "msg_reg_invalid")
        self._menu(fro)

    def _languageMenu(self, fro):
        lines = ["%d. %s" % (i, name) for i, (_code, name) in enumerate(i18n.options(), 1)]
        self._text(fro, "msg_lang_menu", "\n".join(lines))

    def _confirmMenu(self, fro, prompt_key):
        lang = self.languages.get(fro.bare, self.component.getUserLang(fro.bare))
        self._text(fro, "msg_confirm_menu", i18n.t(lang, prompt_key))

    def _requestVcard(self, fro):
        if fro.full not in self.component.clients:
            self._text(fro, "msg_vcard_login"); self._menu(fro); return
        sid = "text-vcard-" + uuid.uuid4().hex
        iq = utils.addsub(None, "iq", utils.COMPONENT_NS, {"type":"get", "to":fro.bare, "from":self.component.cJid, "id":sid})
        utils.addsub(iq, "vCard", utils.VCARD_NS); self.text_vcard_sids[sid] = fro
        self.component.send(utils.tostring(iq)); self._text(fro, "msg_vcard_wait")

    def result_vcard(self, el, fro, ID, success=True):
        requester = self.text_vcard_sids.pop(ID, None)
        if requester is None: return False
        if success and requester.full in self.component.clients:
            xml = utils.retag(el.xml, utils.COMPONENT_NS, utils.CLIENT_NS); xml.attrib.pop("to", None); xml.attrib.pop("from", None); xml.set("type", "set")
            self.component.clients[requester.full].send(utils.tostring(xml)); self._text(requester, "msg_vcard_done")
        else: self._text(requester, "msg_vcard_error")
        self._menu(requester)
        return True

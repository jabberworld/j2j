# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

from twisted.words.protocols.jabber import jid

__id__ = "$Id: utils.py 146 2011-02-01 17:53:27Z binary $"

errorCodeMap = {
	"bad-request": 400,
	"conflict":	409,
	"feature-not-implemented": 501,
	"forbidden": 403,
	"gone":	302,
	"internal-server-error": 500,
	"item-not-found": 404,
	"jid-malformed": 400,
	"not-acceptable": 406,
	"not-allowed": 405,
	"not-authorized": 401,
	"payment-required":	402,
	"recipient-unavailable": 404,
	"redirect": 302,
	"registration-required": 407,
	"remote-server-not-found": 404,
	"remote-server-timeout": 504,
	"resource-constraint": 500,
	"service-unavailable": 503,
	"subscription-required": 407,
	"undefined-condition": 500,
	"unexpected-request": 400
}

def addDiscoItem(query, jid, name=None, node=None):
    item = query.addElement("item")
    item.attributes["jid"] = jid
    if name:
        item.attributes["name"] = name
    if node:
        item.attributes["node"] = node
    return item

def createCommand(iq, node, status, sid):
    command = iq.addElement("command")
    command.attributes["xmlns"] = "http://jabber.org/protocol/commands"
    command.attributes["node"] = node
    command.attributes["status"] = status
    command.attributes["sessionid"] = sid
    return command

def createNote(command, noteType, value):
    note = command.addElement("note", content=value)
    note.attributes["type"] = noteType
    return note

def createForm(iq, formType):
    form = iq.addElement("x")
    form.attributes["xmlns"] = "jabber:x:data"
    form.attributes["type"] = formType
    return form

def addTitle(form, caption):
    title = form.addElement("title", content=caption)
    return title

def addLabel(form, caption):
    label = form.addElement("field")
    label.attributes["type"] = "fixed"
    caption = label.addElement("value", content=caption)
    return label

def addCheckBox(form, name, caption, value):
    checkBox = form.addElement("field")
    checkBox.attributes["type"] = "boolean"
    checkBox.attributes["var"] = name
    checkBox.attributes["label"] = caption
    if value:
        value = "1"
    else:
        value = "0"
    value = checkBox.addElement("value", content=value)
    return checkBox

def addTextBox(form, name, caption, value, required=False):
    textBox = form.addElement("field")
    textBox.attributes["type"] = "text-single"
    textBox.attributes["var"] = name
    textBox.attributes["label"] = caption
    value = textBox.addElement("value", content=value)
    if required:
        textBox.addElement("required")
    return textBox

def addTextPrivate(form,name,caption,value,required=False):
    textBox = form.addElement("field")
    textBox.attributes["type"] = "text-private"
    textBox.attributes["var"] = name
    textBox.attributes["label"] = caption
    value = textBox.addElement("value", content = value)
    if required:
        textBox.addElement("required")
    return textBox

def addMemo(form, name, caption, value):
    Memo = form.addElement("field")
    Memo.attributes["type"] = "text-multi"
    Memo.attributes["var"] = name
    Memo.attributes["label"] = caption
    for string in value.splitlines():
        value = Memo.addElement("value", content=string)
    return Memo

def strToBool(string):
    if string == "0": return False
    return True

def delUri(node):
    if node.uri == "jabber:component:accept" or node.uri == "jabber:client":
        del node.uri
        del node.defaultUri
    for el in node.elements():
        delUri(el)

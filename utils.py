# Part of J2J (http://JRuDevels.org)
# Copyright 2007 JRuDevels.org

# Python3 / slixmpp port helpers.

import copy

XML_NS = 'http://www.w3.org/XML/1998/namespace'

from slixmpp.xmlstream import ET

COMPONENT_NS = 'jabber:component:accept'
CLIENT_NS = 'jabber:client'
COMMANDS_NS = 'http://jabber.org/protocol/commands'
DISCO_INFO_NS = 'http://jabber.org/protocol/disco#info'
DISCO_ITEMS_NS = 'http://jabber.org/protocol/disco#items'
STATS_NS = 'http://jabber.org/protocol/stats'
VCARD_NS = 'vcard-temp'

errorCodeMap = {
    "bad-request": 400,
    "conflict": 409,
    "feature-not-implemented": 501,
    "forbidden": 403,
    "gone": 302,
    "internal-server-error": 500,
    "item-not-found": 404,
    "jid-malformed": 400,
    "not-acceptable": 406,
    "not-allowed": 405,
    "not-authorized": 401,
    "payment-required": 402,
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

def retag(el, src_ns, dst_ns):
    """Return a deep copy of *el* with every element whose tag lives in
    *src_ns* renamed into *dst_ns*. Elements using other namespaces are
    left untouched (including their own xmlns declarations).
    """
    xml = copy.deepcopy(el)
    if xml.tag.startswith('{%s}' % src_ns):
        xml.tag = '{%s}%s' % (dst_ns, xml.tag.split('}', 1)[1])
    for child in list(xml):
        retag_in_place(child, src_ns, dst_ns)
    return xml

def retag_in_place(el, src_ns, dst_ns):
    if el.tag.startswith('{%s}' % src_ns):
        el.tag = '{%s}%s' % (dst_ns, el.tag.split('}', 1)[1])
    for child in list(el):
        retag_in_place(child, src_ns, dst_ns)

def quoteJID(ujid, cJid):
    if ujid == '' or ujid is None:
        return ''
    els = ujid.split('/', 1)
    bare = els[0]
    resource = els[1] if len(els) == 2 else None
    userhost = bare.split('@')
    if len(userhost) == 1:
        qjid = userhost[0]
    else:
        qjid = userhost[0] + '@' + userhost[1]
    qjid = qjid.replace('%', '\\%')
    qjid = qjid.replace('@', '%')
    qjid = qjid + '@' + cJid
    if resource:
        qjid = qjid + '/' + resource
    return qjid

def unquoteJID(qjid, cJid):
    if qjid == '' or qjid is None:
        return ''
    els = qjid.split('/', 1)
    bare = els[0]
    resource = els[1] if len(els) == 2 else None
    ujid = bare.split('@')[0]
    ujid = ujid.replace('%', '@')
    ujid = ujid.replace('\\@', '%')
    if resource:
        ujid = ujid + '/' + resource
    return ujid

def strToBool(string):
    if string == "0":
        return False
    return True

def locname(el):
    """Return the local (namespace stripped) name of an XML element."""
    if '}' in el.tag:
        return el.tag.split('}', 1)[1]
    return el.tag

def nsname(el):
    """Return the namespace URI of an XML element ('' if none)."""
    if '}' in el.tag:
        return el.tag.split('}')[0][1:]
    return ''

def addsub(parent, name, ns, attrib=None, text=None):
    """Create a child element (or a new root when *parent* is None) in
    namespace *ns* named *name*."""
    tag = '{%s}%s' % (ns, name)
    if parent is None:
        child = ET.Element(tag)
    else:
        child = ET.SubElement(parent, tag)
    if attrib:
        for key, value in attrib.items():
            child.set(key, str(value))
    if text is not None:
        child.text = text
    return child

def children(el, name=None):
    """Iterate over the children of a slixmpp stanza or ET element."""
    node = el.xml if hasattr(el, 'xml') else el
    for child in node:
        if name is None or locname(child) == name:
            yield child

# ---- jabber:x:data form builders (used by the register flow) ----

X_DATA_NS = 'jabber:x:data'
X_DATA = '{%s}' % X_DATA_NS

def createForm(iq, formType):
    form = ET.Element(X_DATA + 'x')
    form.set('xmlns', X_DATA_NS)
    form.set('type', formType)
    iq.append(form)
    return form

def addTitle(form, caption):
    el = ET.SubElement(form, X_DATA + 'title')
    el.text = caption
    return el

def addLabel(form, caption):
    label = ET.SubElement(form, X_DATA + 'field')
    label.set('type', 'fixed')
    value = ET.SubElement(label, X_DATA + 'value')
    value.text = caption
    return label

def addCheckBox(form, name, caption, value):
    checkBox = ET.SubElement(form, X_DATA + 'field')
    checkBox.set('type', 'boolean')
    checkBox.set('var', name)
    checkBox.set('label', caption)
    valueEl = ET.SubElement(checkBox, X_DATA + 'value')
    valueEl.text = '1' if value else '0'
    return checkBox

def addTextBox(form, name, caption, value, required=False):
    textBox = ET.SubElement(form, X_DATA + 'field')
    textBox.set('type', 'text-single')
    textBox.set('var', name)
    textBox.set('label', caption)
    valueEl = ET.SubElement(textBox, X_DATA + 'value')
    if value is not None:
        valueEl.text = value
    if required:
        ET.SubElement(textBox, X_DATA + 'required')
    return textBox

def addTextPrivate(form, name, caption, value, required=False):
    textBox = ET.SubElement(form, X_DATA + 'field')
    textBox.set('type', 'text-private')
    textBox.set('var', name)
    textBox.set('label', caption)
    valueEl = ET.SubElement(textBox, X_DATA + 'value')
    if value is not None:
        valueEl.text = value
    if required:
        ET.SubElement(textBox, X_DATA + 'required')
    return textBox

def addMemo(form, name, caption, value):
    memo = ET.SubElement(form, X_DATA + 'field')
    memo.set('type', 'text-multi')
    memo.set('var', name)
    memo.set('label', caption)
    for line in (value or '').splitlines():
        valueEl = ET.SubElement(memo, X_DATA + 'value')
        valueEl.text = line
    return memo

def tostring(xml, xmlns=None):
    """Serialize an ElementTree element to a Unicode string. Namespaces
    are taken from (Clark) tag names and declared on the root, inherited
    by children that use the same namespace."""
    from xml.sax.saxutils import escape as _esc
    if isinstance(xml, str):
        return xml

    out = []

    def ser(el, parent_ns):
        tag = el.tag
        if isinstance(tag, str) and tag.startswith('{'):
            ns = tag.split('}', 1)[0][1:]
            name = tag.split('}', 1)[1]
        else:
            ns = ''
            name = tag
        attrs = ''
        for key, value in el.attrib.items():
            if key == 'xmlns':
                continue
            aname = key
            if aname.startswith('{%s}' % XML_NS):
                aname = 'xml:%s' % aname.split('}', 1)[1]
            attrs += ' %s="%s"' % (aname, _esc(value, {'"': '&quot;'}))
        if ns and ns != parent_ns:
            attrs += ' xmlns="%s"' % ns
        children = list(el)
        pieces = ['<', name, attrs]
        if not children and not el.text:
            pieces.append('/>')
            out.append(''.join(pieces))
            return
        pieces.append('>')
        if el.text:
            pieces.append(_esc(el.text))
        out.append(''.join(pieces))
        for child in children:
            ser(child, ns)
            if child.tail:
                out.append(_esc(child.tail))
        out.append('</%s>' % name)

    ser(xml, '')
    return ''.join(out)

def addDiscoItem(query, jid, name=None, node=None):
    item = ET.SubElement(query, '{%s}item' % DISCO_ITEMS_NS)
    item.set('jid', str(jid))
    if name:
        item.set('name', str(name))
    if node:
        item.set('node', str(node))
    return item

def createCommand(iq, node, status, sessionid):
    command = ET.SubElement(iq, '{%s}command' % COMMANDS_NS)
    command.set('node', node)
    command.set('status', status)
    if sessionid:
        command.set('sessionid', str(sessionid))
    return command

def createNote(command, notetype, text):
    note = ET.SubElement(command, '{%s}note' % COMMANDS_NS)
    note.set('type', notetype)
    note.text = text
    return note

def xdataFields(el):
    """Yield (var, [value texts]) pairs of every submitted jabber:x:data
    field found in the given stanza (workings through iq/query/x or
    command/x)."""
    node = getattr(el, 'xml', el)
    for child in list(node):
        if locname(child) != 'query' and locname(child) != 'command':
            continue
        for x in list(child):
            if locname(x) != 'x' or nsname(x) != X_DATA_NS:
                continue
            if x.get('type') not in ('submit', 'form'):
                continue
            for field in list(x):
                if locname(field) != 'field':
                    continue
                values = []
                for value in list(field):
                    if locname(value) == 'value':
                        values.append(value.text or '')
                yield field.get('var'), values

def xdataValue(el, var):
    for name, values in xdataFields(el):
        if name == var:
            return values[0] if values else ''
    return ''

def xdataValueList(el, var):
    for name, values in xdataFields(el):
        if name == var:
            return values
    return []
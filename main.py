#!/usr/bin/python
# J2J - Jabber-To-Jabber component
# http://JRuDevels.org
# http://wiki.JRuDevels.org
#
# copyright 2007 Dobrov Sergey aka Binary from JRuDevels
#
# License: GPL-v3
#

import j2j
from twisted.words.protocols.jabber import component
from twisted.internet import reactor
import getopt
import sys
from config import Config


def main():
    __all__=['j2j','client','database','roster',
             'utils','adhoc','debug','config']
    revision=0
    date=0

    __id__="$Id: main.py 115 2008-03-02 09:11:37Z binary $"

    try:
        modRev=int(__id__.split(" ")[2])
        modDate=int(__id__.split(" ")[3].replace("-",""))
    except:
        modRev=0
        modDate=0

    if modRev>revision:
        revision=modRev
    if modDate>date:
        date=modDate

    for modName in __all__:
        module=__import__(modName,globals(),locals())
        try:
            modRev=int(module.__id__.split(" ")[2])
            modDate=int(module.__id__.split(" ")[3].replace("-",""))
        except:
            modRev=0
            modDate=0
        if modRev>revision:
            revision=modRev
        if modDate>date:
            date=modDate

    if revision==0:
        revision=''
    else:
        revision='.r'+str(revision)
    if date!=0:
        date=str(date)
        revision=revision+" %s-%s-%s" % (date[:4],date[4:6],date[6:8])

    version="1.1.8"+revision

    from optparse import OptionParser
    parser = OptionParser(version=
                          "Jabber-To-Jabber component version:"+version)
    parser.add_option('-c','--config', metavar='FILE', dest='configFile',
                      help="Read config from custom file")
    (options,args) = parser.parse_args()
    configFile = options.configFile

    if configFile:
        config=Config(configFile)
    else:
        config=Config()

    c=j2j.j2jComponent(reactor,version,config)
    f=component.componentFactory(config.JID,config.PASSWORD)
    connector = component.buildServiceManager(config.JID, config.PASSWORD,
                                     "tcp:%s:%s" % (config.HOST, config.PORT))
    c.setServiceParent(connector)
    connector.startService()
    reactor.run()

if __name__ == "__main__":
    main()
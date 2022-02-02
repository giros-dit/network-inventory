
netconf_filter = open("filter-ietf-interfaces.xml").read()
netconf_reply = m.get(netconf_filter).xml

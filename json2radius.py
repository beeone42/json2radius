#!/usr/bin/env python

import os, json, sys, urllib, urllib2, time, psycopg2

CONFIG_FILE = 'config.json'

"""
Open and load a file at the json format
"""

def open_and_load_json(f):
    if os.path.exists(f):
        with open(f, 'r') as json_file:
            return json.loads(json_file.read())
    else:
        print "File [%s] doesn't exist, aborting." % (f)
        sys.exit(1)

"""
Main
"""

if __name__ == "__main__":
    config = open_and_load_json(CONFIG_FILE)
    url = config['url']
    programs = open_and_load_json(config['programs'])
    vlans = {}
    total = 0
    print url
    try:
        print "downloading datas..."
        res = json.loads(urllib2.urlopen(config['url']).read())
        print "connecting pgsql..."
        co = psycopg2.connect(host = config['db_host'],
                              port = config['db_port'],
                              user = config['db_user'],
                              password = config['db_pass'],
                              database = config['db_data']
                          )
        cur = co.cursor()
        print "lock tables"
        cur.execute("LOCK TABLE radcheck, radreply, radusergroup;")
        print "insert users"
        cur.execute("TRUNCATE radcheck")
        cur.execute("TRUNCATE radreply")
        cur.execute("TRUNCATE radusergroup")
        cur.execute("ALTER SEQUENCE radcheck_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE radreply_id_seq RESTART WITH 1")
        print "Scanning programs..."
        for p in res['programs']:
            if p in programs:
                vlans[p] = programs[p]
            else:
                vlans[p] = config['default_vlan']
            print p + ": vlan " + vlans[p]
        print "Scanning users..."
        for u in res['users']:
            #print u['login'] + " : " + vlans[u['program']]
            total = total + 1
            cur.execute("INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, %s, ':=', %s)",
                        (u['login'], config['db_hash'] + '-Password', config['db_prefix'] + u['password']))
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s, 'Tunnel-Type',             '=', 'VLAN')",
                        [u['login']])
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s, 'Tunnel-Medium-Type',      '=', 'IEEE-802')",
                        [u['login']])
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s, 'Tunnel-Private-Group-Id', '=', %s)",
                        (u['login'], vlans[u['program']]))
            cur.execute("INSERT INTO radusergroup (username, groupname) VALUES (%s, %s)",
                        (u['login'], u['program']))
#        co.commit()
        co.close()
        print "done (%d users)" % total
    except Exception as e:
        print "Error:"
        print e.message
        print sys.exc_info()
        print "Exiting"

import sqlite3, sys
db = sys.argv[1] if len(sys.argv) > 1 else 'db.sqlite'
c = sqlite3.connect(db)
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table' order by name")]
print("TABLES:", tabs)
for t in tabs:
    n = c.execute('select count(*) from "%s"' % t).fetchone()[0]
    print("  %-34s %d rows" % (t, n))

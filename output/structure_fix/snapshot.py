import sys, pathlib, hashlib, json
root=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root))
from database.common import settings
import mysql.connector
result={}
with mysql.connector.connect(**settings()) as cn:
    cur=cn.cursor()
    cur.execute('SHOW TABLES')
    tables=[r[0] for r in cur.fetchall()]
    for table in tables:
        assert table.replace('_','').isalnum()
        cur.execute('SHOW CREATE TABLE `'+table+'`')
        ddl=cur.fetchone()[1]
        cur.execute('SELECT * FROM `'+table+'`')
        rows=sorted(json.dumps(r,default=str) for r in cur.fetchall())
        result[table]={'rows':len(rows),'sha256':hashlib.sha256((ddl+'\n'+'\n'.join(rows)).encode()).hexdigest()}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2))
print('Read-only schema/data snapshot:',len(result),'tables')

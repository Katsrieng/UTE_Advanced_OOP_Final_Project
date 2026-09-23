"""SQL repositories map persistent columns to the existing Jinja row contract."""
from datetime import date, datetime
from app.database import PersistenceError

class EntityRepository:
    table=''
    pk=''
    fields={}
    active=False
    def __init__(self,db): self.db=db

    @property
    def projection(self):
        parts=[f't.{self.pk} AS id']+[f't.{column} AS `{key}`' for key,column in self.fields.items()]
        if self.active: parts.append("CASE WHEN t.is_active THEN 'ACTIVE' ELSE 'INACTIVE' END AS status")
        parts.append('t.created_at AS created')
        if self.table not in ('stock_movements','invoices'): parts.append('t.updated_at AS updated')
        return ','.join(parts)

    def map(self,row):
        if row is None: return None
        return {key:(value.isoformat()[:10] if isinstance(value,(date,datetime)) else value) for key,value in row.items()}

    def select(self,where='',params=(),suffix=''):
        sql=f'SELECT {self.projection} FROM {self.table} t'
        if where: sql+=' WHERE '+where
        return [self.map(row) for row in self.db.query(sql+' '+suffix,params)]

    def get(self,item_id,lock=False):
        rows=self.select(f't.{self.pk}=%s',(item_id,), 'FOR UPDATE' if lock else '')
        return rows[0] if rows else None

    def save(self,values,item_id=None):
        data={column:values[key] for key,column in self.fields.items() if key in values}
        if self.active and 'status' in values: data['is_active']=values['status']=='ACTIVE'
        for optional in ('vin','plate_number','email'):
            if optional in data and data[optional]=='': data[optional]=None
        if not data: return self.get(item_id)
        if item_id:
            self.db.execute(f'UPDATE {self.table} SET '+','.join(f'{k}=%s' for k in data)+f' WHERE {self.pk}=%s',tuple(data.values())+(item_id,))
        else:
            item_id=self.db.execute(f'INSERT INTO {self.table} ('+','.join(data)+') VALUES ('+','.join(['%s']*len(data))+')',tuple(data.values()))
        return self.get(item_id)

    def exists(self,key,value,exclude=None):
        if key not in self.fields: return False
        rows=self.db.query(f'SELECT {self.pk} FROM {self.table} WHERE {self.fields[key]}=%s AND (%s IS NULL OR {self.pk}<>%s) LIMIT 1',(value,exclude,exclude))
        return bool(rows)

class VehicleRepository(EntityRepository):
    table='vehicles'; pk='vehicle_id'
    fields=dict(code='vehicle_code',vin='vin',plate='plate_number',brand='brand',model='model',year='vehicle_year',color='color',purchase_price='purchase_price',price='selling_price',status='status',image='image_path',mileage='mileage',fuel='fuel')
    def references_image(self,image):
        return bool(self.db.query('SELECT vehicle_id FROM vehicles WHERE image_path=%s LIMIT 1',(image,)))
    def filter_options(self):
        return self.db.query('SELECT DISTINCT brand,vehicle_year FROM vehicles ORDER BY brand,vehicle_year DESC')

class CustomerRepository(EntityRepository):
    table='customers'; pk='customer_id'; active=True
    fields=dict(code='customer_code',name='full_name',phone='phone',email='email',address='address')
    @property
    def projection(self):
        return super().projection+",(SELECT COUNT(*) FROM sales s WHERE s.customer_id=t.customer_id AND s.status='COMPLETED') AS purchases"

class UserRepository(EntityRepository):
    table='users'; pk='user_id'; active=True
    fields=dict(name='full_name',username='username',email='email')
    @property
    def projection(self):
        return super().projection+",COALESCE((SELECT GROUP_CONCAT(r.role_name ORDER BY r.role_id SEPARATOR ', ') FROM user_roles ur JOIN roles r ON r.role_id=ur.role_id AND r.is_active=1 WHERE ur.user_id=t.user_id),'') AS role"
    def credentials(self,username):
        rows=self.db.query('SELECT user_id,password_hash,is_active FROM users WHERE username=%s',(username,))
        return rows[0] if rows else None
    def permissions(self,user_id):
        return {row['permission_name'] for row in self.db.query('SELECT DISTINCT p.permission_name FROM users u JOIN user_roles ur ON ur.user_id=u.user_id JOIN roles r ON r.role_id=ur.role_id JOIN role_permissions rp ON rp.role_id=r.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE u.user_id=%s AND u.is_active=1 AND r.is_active=1 AND p.is_active=1',(user_id,))}
    def set_password(self,user_id,password_hash):
        self.db.execute('UPDATE users SET password_hash=%s WHERE user_id=%s',(password_hash,user_id))
    def create(self,values,password_hash):
        return self.db.execute('INSERT INTO users (username,full_name,email,password_hash,is_active) VALUES (%s,%s,%s,%s,%s)',(values['username'],values['name'],values['email'],password_hash,values['status']=='ACTIVE'))
    def assign_role(self,user_id,role_id):
        self.db.execute('DELETE FROM user_roles WHERE user_id=%s',(user_id,))
        self.db.execute('INSERT INTO user_roles (user_id,role_id) VALUES (%s,%s)',(user_id,role_id))

class RoleRepository:
    def __init__(self,db): self.db=db
    def all(self):
        result={r['role_name']:[] for r in self.db.query('SELECT role_name FROM roles WHERE is_active=1 ORDER BY role_id')}
        for row in self.db.query('SELECT r.role_name,p.permission_name FROM roles r JOIN role_permissions rp ON rp.role_id=r.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE r.is_active=1 AND p.is_active=1'):
            result[row['role_name']].append(row['permission_name'])
        return result
    def get_by_name(self,name,lock=False):
        rows=self.db.query('SELECT role_id,role_name,is_active FROM roles WHERE role_name=%s'+(' FOR UPDATE' if lock else ''),(name,))
        return rows[0] if rows else None
    def update_permissions(self,role_id,permissions):
        self.db.execute('DELETE FROM role_permissions WHERE role_id=%s',(role_id,))
        for name in permissions:
            self.db.execute('INSERT INTO role_permissions (role_id,permission_id) SELECT %s,permission_id FROM permissions WHERE permission_name=%s AND is_active=1',(role_id,name))

class PermissionRepository:
    def __init__(self,db): self.db=db
    def groups(self):
        groups={}
        for row in self.db.query('SELECT permission_name,module FROM permissions WHERE is_active=1 ORDER BY permission_id'):
            groups.setdefault(row['module'].title(),[]).append(row['permission_name'])
        return groups

class StockMovementRepository(EntityRepository):
    table='stock_movements'; pk='movement_id'
    fields=dict(vehicle_id='vehicle_id',user_id='user_id',movement='movement_type',date='movement_date',reason='reason',quantity='quantity')
    @property
    def projection(self):
        return super().projection+', (SELECT full_name FROM users WHERE user_id=t.user_id) AS staff'

class SaleRepository(EntityRepository):
    table='sales'; pk='sale_id'
    fields=dict(code='sale_code',user_id='user_id',customer_id='customer_id',vehicle_id='vehicle_id',date='sale_date',price='sale_price',discount='discount_amount',total='total_amount',status='status')
    @property
    def projection(self):
        return super().projection+', (SELECT full_name FROM users WHERE user_id=t.user_id) AS staff'

class InvoiceRepository(EntityRepository):
    table='invoices'; pk='invoice_id'
    fields=dict(code='invoice_number',sale_id='sale_id',date='issue_date',total='total_amount')
    def for_sale(self,sale_id):
        rows=self.select('t.sale_id=%s',(sale_id,))
        return rows[0] if rows else None

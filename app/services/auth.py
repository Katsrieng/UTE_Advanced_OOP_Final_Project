"""Authentication and user/role administration; hashes never reach templates."""
from werkzeug.security import check_password_hash,generate_password_hash
from app.database import PersistenceError

class AuthService:
    def __init__(self,repo): self.repo=repo
    def authenticate(self,username,password):
        row=self.repo.users.credentials(username)
        if row and row['is_active'] and check_password_hash(row['password_hash'],password):
            return self.repo.get('users',row['user_id'])
        return None

class UserService:
    def __init__(self,repo): self.repo=repo
    def save(self,values,item_id=None,actor_id=None):
        values=dict(values); password=values.pop('password','')
        if (not item_id or password) and not 10<=len(password)<=250:
            raise ValueError('Use a password of 10 to 250 characters.')
        if '@' not in values.get('email','') or '.' not in values['email'].split('@')[-1]:
            raise ValueError('Enter a valid email address.')
        with self.repo.transaction():
            # Serialize access edits on the Admin role before locking individual users.
            admin=self.repo.role_repository.get_by_name('Admin',lock=True)
            role=self.repo.role_repository.get_by_name(values['role'])
            if not role or not role['is_active']: raise ValueError('Choose an active role.')
            old=self.repo.get('users',item_id,lock=True) if item_id else None
            if item_id and not old: raise ValueError('User not found.')
            if old:
                role_ids=self.repo.db.query('SELECT role_id FROM user_roles WHERE user_id=%s',(item_id,))
                existing={r['role_id'] for r in role_ids}
                changing=existing!={role['role_id']} or values['status']!='ACTIVE'
                if item_id==actor_id and changing:
                    raise ValueError('Use another administrator account to change your own access.')
                if admin['role_id'] in existing and changing:
                    count=self.repo.db.query('SELECT COUNT(*) AS n FROM users u JOIN user_roles ur ON ur.user_id=u.user_id WHERE u.is_active=1 AND ur.role_id=%s',(admin['role_id'],))[0]['n']
                    if count<=1: raise ValueError('Keep at least one active administrator.')
                self.repo.save('users',values,item_id)
                if password: self.repo.users.set_password(item_id,generate_password_hash(password))
            else:
                item_id=self.repo.users.create(values,generate_password_hash(password))
            self.repo.users.assign_role(item_id,role['role_id'])
            return self.repo.get('users',item_id)

    def permissions(self,role_name,names):
        with self.repo.transaction():
            role=self.repo.role_repository.get_by_name(role_name,lock=True)
            if not role or not role['is_active']: raise ValueError('Role not found.')
            if role_name=='Admin': raise ValueError('Administrator permissions are protected.')
            allowed={p for group in self.repo.permission_repository.groups().values() for p in group}
            if not set(names)<=allowed: raise ValueError('Choose valid permissions.')
            self.repo.role_repository.update_permissions(role['role_id'],set(names))

"""Real MySQL tests are opt-in and own a fresh uniquely named database per test."""
import os
import unittest
from uuid import uuid4
import mysql.connector
from database.common import settings, create_schema
from database.seed import seed_database

class MySQLTestCase(unittest.TestCase):
    def setUp(self):
        if os.environ.get('RUN_MYSQL_TESTS') != '1':
            self.skipTest('Set RUN_MYSQL_TESTS=1 to run isolated MySQL integration tests')
        self.db_config = settings()
        if self.db_config['port'] != 3307:
            raise RuntimeError('This local test workflow requires MySQL port 3307.')
        self.test_db = 'autovault_test_' + uuid4().hex
        self.db_config['database'] = self.test_db
        server=dict(self.db_config); server.pop('database')
        with mysql.connector.connect(**server) as cn:
            with cn.cursor() as cur:
                cur.execute('SELECT VERSION()')
                version=cur.fetchone()[0]
                if not version.startswith('8.') or 'MariaDB' in version:
                    raise RuntimeError('Tests require actual MySQL 8.')
                cur.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s',(self.test_db,))
                if cur.fetchone(): raise RuntimeError('Refusing to reuse an existing test database')
        create_schema(self.db_config)
        self.addCleanup(self.drop_owned_database)
        seed_database(self.db_config)

    def drop_owned_database(self):
        assert self.test_db.startswith('autovault_test_') and len(self.test_db)==47
        server=dict(self.db_config); server.pop('database')
        with mysql.connector.connect(**server) as cn:
            with cn.cursor() as cur:
                cur.execute('DROP DATABASE `'+self.test_db+'`')

    def app_config(self):
        return {'TESTING':True, 'SECRET_KEY':'test-only-secret', 'DATABASE':self.db_config}

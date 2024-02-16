import unittest
from flask import current_app,url_for,json
from app import create_app,db
from app.models import *
from app.main import views
from app import *
class BasicTestCase(unittest.TestCase):
    def setup(self):
        self.client = self.app.test_client()
        self.app=create_app('testing')
        self.app_context=self.app.app_context()
        self.app_context.push()
        db.create_all()


    def teardown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exits(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTure(current_app.config['TESTING'])


    def test_password_setter(self):
        u = User(password='fff')
        self.assertTrue(u.password_hash is not None)


    def test_password_verification(self):
        u = User(password='fff')
        self.assertTrue(u.verify_password('fff'))
        self.assertFalse(u.verify_password('flf'))

    def test_password_salts_are_random(self):
        u = User(password='fff')
        u2 = User(password='fff')
        self.assertTrue(u.password_hash != u2.password_hash)

    def test_valid_reset_token(self):
        u = User(password='fff')
        db.session.add(u)
        db.session.commit()

        self.assertTrue(u.verify_password('fff'))

    def test_invalid_reset_token(self):
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        self.assertTrue(u2.verify_password('dog'))




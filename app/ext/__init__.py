
from flask.app import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_sitemap import Sitemap
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

class AppHelper(object):
    def init_app(self, app: Flask, db=None, directory=None, **kwargs):
        self.app = app
    def config_update(self):
        with db.get_engine(app=self.app).connect() as conn:
            objs = conn.execute("select * from setting")
            for o in objs:
                if o.skey:
                    if o.skey in ['h3blog_comment','h3blog_register_invitecode']:
                        v = True if o.svalue == '1' else False
                        self.app.config[o.skey.upper()] = v
                    else:
                        self.app.config[o.skey.upper()] = o.svalue

class DBConfig(object):
    def init_app(self, app, db=None):
        try:
            with db.get_engine(app=app).connect() as conn:
                objs = conn.execute("select * from setting")
                for o in objs:
                    if o.skey:
                        if o.skey in ['h3blog_comment','h3blog_register_invitecode']:
                            v = True if o.svalue == '1' else False
                            app.config[o.skey.upper()] = v
                        else:
                            app.config[o.skey.upper()] = o.svalue
        except:
            print('连接数据库失败或setting表不存在')
        
db = SQLAlchemy()
sitemap = Sitemap()
login_manager = LoginManager()
migrate = Migrate()
app_helper = AppHelper()
csrf = CSRFProtect()
db_config = DBConfig()

timez = pytz.timezone('Asia/Shanghai')
scheduler = APScheduler(scheduler=BackgroundScheduler(timezone = timez))


def check_db_uri(uri: str) ->bool:
    """
    检查数据库连接是否可用
    """
    from sqlalchemy import create_engine
    try:
        engine = create_engine(uri)
        conn = engine.connect()
        return True
    except Exception as e:
        return False
    return False
    



@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    try:
        return User.query.get(int(user_id))
    except:
        return None

login_manager.session_protection = 'strong'
# login_manager.login_view = 'admin.login'
# login_manager.blueprint_login_views = {
#         'admin': 'admin.login',
#         'main' : 'main.login'
#     }
# login_manager.login_message = 'Your custom message'
login_manager.login_message_category = 'warning'

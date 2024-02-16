from app.settings import {{import_config}} as Cfg

class Config(Cfg):
    SQLALCHEMY_DATABASE_URI = '{{db_uri}}'
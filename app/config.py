from app.settings import DevelopmentConfig as Cfg

class Config(Cfg):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data-dev.db'
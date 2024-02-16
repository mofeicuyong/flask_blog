import os
import logging
import click
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import get_debug_queries
from flask_wtf.csrf import CSRFError
from app.util import pretty_date
from app.ext import db, sitemap, login_manager, csrf, migrate, app_helper, db_config, scheduler
from app.settings import *
from app.template_global import register_template_filter, register_template_global
from app.models import AccessLog

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    """ 使用工厂函数初始化程序实例"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['CONFIG_NAME'] = config_name


    check_setup(app)

    register_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_errors(app)
    register_shell_context(app)
    register_request_handlers(app)
    register_jiaja2_filters(app)
    register_template_filter(app)
    register_template_global(app)

    return app


def check_setup(app: Flask) -> None:
    """
    启动检测自定义配置文件是否存在
    """
    app.start = False
    from app.settings import _exist_config
    if _exist_config(app):
        try:
            from app.config import Config
            app.config.from_object(Config)
            app.start = True
        except:
            pass

    @app.before_request
    def request_check_start():
        if app.start:
            return
        ends = frozenset(["admin.setup", "admin.static"])
        if request.endpoint in ends:
            return
        if not _exist_config(app):
            return redirect(url_for("admin.setup"))
        return


def register_logging(app):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = RotatingFileHandler(os.path.join(basedir, 'logs/xjzbm.log'),
                                       maxBytes=10 * 1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)
    if not app.debug:
        if not os.path.exsts('logs'):
            os.mkdir('logs')
        l=RotatingFileHandler(os.path.join(basedir, 'logs/xjzbm.log'),
                            maxBytes=10 * 1024 * 1024, backupCount=10)
        l.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s[in %(pathname)s:%(lineno)d]'))
        l.setLevel(logging.INFO)
        app.logger.addHandler(l)
        app.logger.setLevel(logging.INFO)
        app.logger.info('start')
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.setLevel(logging.DEBUG)
    app.logger.setLevel(logging.WARNING)
    app.logger.info('start:\n')
    app.logger.debug('debug:\n')
    app.logger.warning('warning:\n')

def register_extensions(app):
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    sitemap.init_app(app)
    migrate.init_app(app, db=db)
    app_helper.init_app(app)
    db_config.init_app(app, db=db)




def register_blueprints(app):
    # 注册蓝本 main
    from app.main import main as main_blueprint, change_static_folder
    change_static_folder(main_blueprint, app.config['H3BLOG_TEMPLATE'])
    app.register_blueprint(main_blueprint)

    # 注册蓝本 admin
    from app.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    from app.vip import vip as vip_blueprint
    app.register_blueprint(vip_blueprint, url_prefix='/vip')

    login_manager.blueprint_login_views = {
        'admin': 'admin.login',
        'main': 'main.login',
        'vip':'vip.login'
    }


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Article, Category, \
            Tag, article_tag, Recommend, Picture, Setting
        return dict(db=db, User=User, Article=Article, \
                    Category=Category, Tag=Tag, Recommend=Recommend, \
                    AccessLog=AccessLog, Picture=Picture, Setting=Setting)


def register_errors(app):
    pass


def register_request_handlers(app):
    from flask_login import current_user
    @app.context_processor
    def context_processor():
        '''
        上下文处理器, 返回的字典可以在全部模板中使用
        '''
        return {'current_user': current_user}

    @app.before_request
    def before_app_request():
        user_agent = request.headers.get("User-Agent")
        if user_agent is None:
            return
        remark = None
        if 'Baiduspider' in user_agent:
            remark = '百度'
        if 'Bytespider' in user_agent:
            remark = '头条搜索'
        if 'YisouSpider' in user_agent:
            remark = '神马搜索'
        if 'Sogou' in user_agent:
            remark = '搜狗'
        if 'Sosospider' in user_agent:
            remark = '搜搜'

        if remark:
            accessLog = AccessLog(ip=request.remote_addr,
                                  url=request.path,
                                  remark=remark)
            db.session.add(accessLog)

    @app.after_request
    def query_profiler(response):
        for q in get_debug_queries():
            if q.duration >= app.config['H3BLOG_SLOW_QUERY_THRESHOLD']:
                app.logger.warning(
                    'Slow query: Duration: %fs\n Context: %s\nQuery: %s\n '
                    % (q.duration, q.context, q.statement)
                )
        return response


def register_jiaja2_filters(app):
    env = app.jinja_env
    env.filters['pretty_date'] = pretty_date  # 注册自定义过滤器


def register_commands(app):
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """Initialize the database."""
        if drop:
            click.confirm('This operation will delete the database, do you want to continue?', abort=True)
            db.drop_all()
            click.echo('Drop tables.')
        db.create_all()
        click.echo('Initialized database.')

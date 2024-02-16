from typing import Any
from app import util

from . import db
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import hashlib, os
import markdown
from flask_login import current_user
from flask import url_for, request


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    email_state = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64), nullable=False, default='')
    website = db.Column(db.String(128), nullable=False, default='', comment='网址')
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    status = db.Column(db.Boolean, default=False)
    role = db.Column(db.Integer, default=2, comment='1=管理员,0=普通账号,3=vip')
    avatar = db.Column(db.String(120), default='')
    articles = db.relationship('Article', backref='author', lazy='dynamic')

    @property
    def password(self):
        raise ArithmeticError('非明文密码，不可读。')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password=password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password=password)

    def is_admin(self):
        return self.role == 1

    def is_vip(self):
        return self.role == 3

    @property
    def role_name(self):
        name = ''
        if self.role == 1:
            name = '管理员'
        elif self.role == 3:
            name = 'VIP会员'
        elif self.role == 2:
            name = '普通会员'
        else:
            name = '未知'
        return name

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def is_author(self):
        return Article.query.filter_by(author_id=self.id).first()

    def __repr__(self):
        return '<%r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64), unique=True, index=True)
    desp = db.Column(db.String(300))
    tpl_list = db.Column(db.String(300))  # 列表模板
    tpl_page = db.Column(db.String(300))  # 单页/详情模板
    tpl_mold = db.Column(db.String(20))  # 模板类型 list,single_page
    content = db.Column(db.Text)  # 如果是单页，可以录入信息内容
    seo_title = db.Column(db.String(100))
    seo_description = db.Column(db.String(300))
    seo_keywords = db.Column(db.String(300))
    sn = db.Column(db.Integer, default=0)  # 排序编号
    visible = db.Column(db.Boolean, default=True)  # 是否隐藏
    articles = db.relationship('Article', backref='category', lazy='dynamic')
    icon = db.Column(db.String(128), default='')

    def __repr__(self):
        return '<Name %r>' % self.name


article_tag = db.Table('article_tag',
                       db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
                       db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))


class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False, unique=True, index=True)
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    visible = db.Column(db.Boolean, default=True)  # 是否隐藏

    @classmethod
    def add(self, name: str) -> Any:
        """添加标签"""
        tag = Tag.query.filter(Tag.name == name).first()
        if tag is not None:
            return tag
        code = util.get_short_id()
        while db.session.query(Tag.query.filter(Tag.code == code).exists()).scalar():
            code = util.get_short_id()
        tag = Tag(name=name, code=code, visible=True)
        db.session.add(tag)
        db.session.commit()
        return tag

    def __repr__(self):
        return '<Name %r>' % self.name


class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), index=True)
    name = db.Column(db.String(64), index=True, unique=True)
    editor = db.Column(db.String(10), nullable=False, default='')
    content = db.Column(db.Text)
    content_html = db.Column(db.Text)
    summary = db.Column(db.String(300))
    thumbnail = db.Column(db.String(200))
    state = db.Column(db.Integer, default=0)
    vc = db.Column(db.Integer, default=0)
    comment_num = db.Column(db.Integer, nullable=False, default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    tags = db.relationship('Tag', secondary=article_tag, backref=db.backref('articles', lazy='dynamic'), lazy='dynamic')
    h_content = db.Column(db.String(800), nullable=False, default='')  # 隐藏内容
    h_role = db.Column(db.Integer, default=0, comment='1=管理员,2=普通账号,3=vip')  # 那个角色可以看见隐藏的内容
    is_crawl = db.Column(db.Integer, default=0, comment='0=作者字写，1=抓取内容')
    origin_url = db.Column(db.String(200), default='', comment='抓取内容的原始url')
    origin_author = db.Column(db.String(100), default='', comment='原作者')

    def content_to_html(self):
        return markdown.markdown(self.content, extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
        ])

    # @property
    # def author(self):
    #     """返回作者对象"""
    #     return User.query.get(self.author_id)

    @property
    def category(self):
        """返回文章分类对象"""
        return Category.query.get(self.category_id)

    @property
    def category_name(self):
        """返回文章分类名称，主要是为了使用 flask-wtf 的 obj 返回对象的功能"""
        return Category.query.get(self.category_id).name

    @property
    def previous(self):
        """用于分页显示的上一页"""
        a = self.query.filter(Article.state == 1, Article.id < self.id). \
            order_by(Article.timestamp.desc()).first()
        return a

    @property
    def next(self):
        """用于分页显示的下一页"""
        a = self.query.filter(Article.state == 1, Article.id > self.id). \
            order_by(Article.timestamp.asc()).first()
        return a

    @property
    def tag_names(self):
        """返回文章的标签的字符串，用英文‘, ’分隔，主要用于修改文章功能"""
        tags = []
        for tag in self.tags:
            tags.append(tag.name)
        return ', '.join(tags)

    @property
    def thread_key(self):  # 用于评论插件
        return hashlib.new(name='md5', string=str(self.id)).hexdigest()

    @property
    def show_h_content(self) -> str:
        if current_user.is_authenticated and current_user.role == self.h_role:
            return self.h_content
        else:
            # url = url_for('main.profile')
            url = url_for('main.login') + '?next=' + request.path
            repl = '''
            <p class="border border-warning p-2 text-center">
                本文隐藏内容 <a href="{}">登陆</a> 后才可以浏览
            </p>
            '''.format(url)
            return repl

    def __repr__(self):
        return '<Title %r>' % self.title


class Comment(db.Model):
    '''
    评论
    '''
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default=0)
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'), lazy=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False, default=0, comment='关联的文章id')
    article = db.relationship('Article', backref=db.backref('comments', lazy='dynamic', order_by=id.desc()), lazy=True)
    content = db.Column(db.String(1024))
    reply_id = db.Column(db.Integer, db.ForeignKey('comment.id'), default=None, comment='回复对应的评论id')
    replies = db.relationship('Comment', back_populates='comment')
    comment = db.relationship('Comment', back_populates='replies', remote_side=[id])
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return '<user_id: %r, article_id: %r,reply_id: %r, content: %r>' % (
        self.user_id, self.article_id, self.reply_id, self.content)


class Recommend(db.Model):
    '''
    推荐
    '''
    __tablename__ = 'recommend'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    img = db.Column(db.String(200))
    url = db.Column(db.String(200))
    sn = db.Column(db.Integer, default=0)
    state = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class AccessLog(db.Model):
    '''
    请求日志
    '''
    __tablename__ = 'access_log'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(20))
    url = db.Column(db.String(120))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    remark = db.Column(db.String(32))


class Picture(db.Model):
    '''
    图片
    '''
    __tablename__ = 'picture'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    url = db.Column(db.String(120))
    remark = db.Column(db.String(32))


class InvitationCode(db.Model):
    '''
    邀请码
    '''
    __tablename__ = 'invitation_code'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    user = db.Column(db.String(64))
    state = db.Column(db.Boolean, default=True)


class Setting(db.Model):
    '''
    数据库配置信息
    '''
    __tablename__ = 'setting'
    id = db.Column(db.Integer, primary_key=True)
    skey = db.Column(db.String(64), index=True, unique=True)
    svalue = db.Column(db.String(800), default='')


class SpiderInclude(db.Model):
    """收录"""
    __tablename__ = 'spider_include'
    id = db.Column(db.Integer, primary_key=True)
    search_engine = db.Column(db.String(64), nullable=False, default='', comment='搜索引擎')
    num = db.Column(db.Integer, nullable=False, default=0, comment='收录数量')
    time_label = db.Column(db.String(20), nullable=False, default='', comment='时间标签')
    ctime = db.Column(db.DateTime, default=datetime.now, comment='时间')

    def to_dict(self):
        d = {i.name: getattr(self, i.name) for i in self.__table__.columns}
        return d

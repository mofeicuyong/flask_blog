from sys import prefix
from typing import Set
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify, \
    send_from_directory, make_response, session
from flask.helpers import send_file
from flask_login import login_user, logout_user, login_required, current_user
from wtforms.fields.core import SelectField

from app import util
from . import vip
from app.ext import db, app_helper, check_db_uri
from .forms import AddAdminForm, LoginForm, AddUserForm, DeleteUserForm, EditUserForm, ArticleForm, \
    ChangePasswordForm, AddFolderForm, CategoryForm, RecommendForm, InvitcodeForm, OnlineToolForm, \
    SettingForm, ConfigForm, TagForm
from app.models import User, Category, Tag, Article, Recommend, AccessLog, Picture, InvitationCode, \
     Setting, SpiderInclude
import os, io
from datetime import datetime, timedelta
from app.util import  isAjax, upload_file_qiniu, allowed_file, \
    baidu_push_urls, strip_tags, gen_invit_code
from app.settings import config, exist_config, create_config


@vip.route("/setup", methods=['GET', 'POST'])
def setup():
    if exist_config():
        # 已经存在配置文件
        return redirect('/')
    step = request.args.get("step", type=int)
    if step == 1:  # 要求录入数据库配置
        form = ConfigForm()
        return render_template("vip/setup/setup-step1.html", form=form)
    elif step == 2:  # 验证数据库配置是否可用，如果可用下一步录入管理员账号
        return setup_step2()
    elif step == 3:  # 保存管理员账号
        form = AddAdminForm()
        if request.method == 'POST':
            session['username'] = form.username.data.strip()
            session['email'] = form.email.data.strip()
            session['password'] = form.password.data.strip()
        return render_template("vip/setup/setup-step3.html")
    elif step == 4:  # 安装数据
        # 1、检查并连接数据库
        uri = session['dburi']
        if check_db_uri(uri):
            create_config(uri)
            try:
                from app.config import Config
                current_app.config.from_object(Config)
                db.create_all()
                # 创建管理员账号
                u = User(username=session['username'],
                         email=session['email'],
                         password=session['password'],
                         status=True, role=3
                         )
                db.session.add(u)
                db.session.commit()
                return render_template("vip/setup/setup-step4.html")
            except Exception as e:
                print(e)
                return render_template("vip/setup/setup-step3.html")
    form = ConfigForm()
    return render_template("vip/setup/setup.html", form=form)


def setup_step2():
    form = ConfigForm()
    if form.validate_on_submit and request.method == 'POST':
        uri = form.uri.data.strip()
        if not check_db_uri(uri):
            return render_template('vip/setup/setup-step1.html', form=form)
        session['dburi'] = uri
        form = AddAdminForm()
        return render_template("vip/setup/setup-step2.html", addAdminForm=form)
    return render_template("vip/setup/setup-step1.html", form=form)


@vip.route('/', methods=['GET', 'POST'])
@login_required
def index():
    current_user.ping()
    NOW = datetime.now()
    includes = SpiderInclude.query.filter(SpiderInclude.ctime > NOW - timedelta(days=30)). \
        order_by(SpiderInclude.ctime.asc()).all()
    list = [i.to_dict() for i in includes]
    if current_user._get_current_object().role==1:
        return render_template('admin/index.html',spinderIncludes=list)
    return render_template('vip/index.html', spinderIncludes=list)


@vip.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(prefix='login')
    user = User.query.filter_by(status=True).first()
    if not user:
        add_admin_form = AddAdminForm(prefix='add_admin')
        if request.method == 'POST' and add_admin_form.validate_on_submit():
            u = User(username=add_admin_form.username.data.strip(),
                     email=add_admin_form.email.data.strip(),
                     password_hash=add_admin_form.password.data.strip(),
                     status=True, role=1
                     )
            db.session.add(u)
            db.session.commit()
            login_user(user=u)
            return redirect(url_for('vip.write'))

        return render_template('vip/add_admin.html', addAdminForm=add_admin_form)
    else:
        if request.method == 'POST' and login_form.validate_on_submit():
            u = User.query.filter_by(username=login_form.username.data.strip()).first()
            if u is None:
                flash({'error': '帐号未注册！'})
            elif u is not None and u.verify_password(login_form.password.data.strip()) and u.status:
                login_user(user=u, remember=login_form.remember_me.data)
                return redirect(url_for('vip.index'))
            elif not u.status:
                flash({'error': '用户已被管理员注销！'})
            elif not u.verify_password(login_form.password.data.strip()):
                flash({'error': '密码不正确！'})

    return render_template('vip/login.html', loginForm=login_form)


@vip.route('/logout')
@login_required
def logout():
    """
    退出系统
    """
    logout_user()
    return redirect(url_for('main.index'))


@vip.route('/articles', methods=['GET'])
@login_required
def articles():
    title = request.args.get('title', '')
    page = request.args.get('page', 1, type=int)
    articles = Article.query.filter(
        Article.title.like("%" + title + "%") if title is not None else ''
    ).order_by(Article.timestamp.desc()).paginate(page, per_page=current_app.config['H3BLOG_POST_PER_PAGE'],
                                                  error_out=False)

    return render_template('vip/articles.html', articles=articles, title=title)


@vip.route('/article/edit/<id>', methods=['GET'])
@login_required
def article_edit(id):
    '''加载编辑文章'''
    article = Article.query.get(int(id))
    form = ArticleForm(obj=article)
    # 当请求参数editor为空，使用文章原来编辑器
    editor = request.args.get('editor', article.editor)
    form.editor.data = editor
    form.tags.data = ','.join([t.name for t in article.tags.all()])
    if editor == 'tinymce':
        return render_template('vip/write_tinymce.html', form=form)
    return render_template('vip/write.html', form=form)


@vip.route('/article/write', methods=['GET', 'POST'])
@login_required
def write():
    form = ArticleForm()
    if request.method == 'POST' and form.validate_on_submit():
        # --------以下功能是增加文章的分类
        cty = Category.query.get(int(form.category_id.data))
        a = None
        if form.id.data:
            a = Article.query.get(int(form.id.data))
        if a:
            a.title = form.title.data.strip()
            a.editor = form.editor.data
            a.content = form.content.data
            a.content_html = a.content_to_html() if a.editor == 'markdown' else form.content_html.data
            a.summary = form.summary.data
            a.thumbnail = form.thumbnail.data
            a.category = cty
            a.name = form.name.data.strip()
            a.state = form.state.data
            a.timestamp = form.timestamp.data
            a.h_role = form.h_role.data
            a.h_content = form.h_content.data
            if not a.name and len(a.name) == 0:
                a.name = a.id
            db.session.commit()
        else:
            # --------以下功能是将文章信息插入数据库
            a = Article(title=form.title.data.strip(), content=form.content.data, editor=form.editor.data,
                        thumbnail=form.thumbnail.data, name=form.name.data.strip(),
                        state=form.state.data, summary=form.summary.data,
                        category=cty, author=current_user._get_current_object()
                        )
            a.content_html = a.content_to_html() if a.editor == 'markdown' else form.content_html.data
            db.session.add(a)
            db.session.commit()
            if not a.name and len(a.name) == 0:
                a.name = a.id
                db.session.commit()
        # --------以下功能是将文章标识插入数据库
        a.tags = []
        for tg in form.tags.data.split(','):
            if tg.strip() == '':
                continue
            t = Tag.add(tg)
            if t not in a.tags:
                a.tags.append(t)
        if isAjax():
            msg = '发布成功' if int(form.state.data) == 1 else '保存成功'
            return jsonify({'code': 1, 'msg': msg, 'id': a.id})

    editor = request.args.get('editor', current_app.config.get('H3BLOG_EDITOR'))
    form.editor.data = editor
    if editor == 'tinymce':
        return render_template('vip/write_tinymce.html', form=form)
    return render_template('vip/write.html', form=form)



@vip.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    add_user_form = AddUserForm(prefix='add_user')
    delete_user_form = DeleteUserForm(prefix='delete_user')
    if request.method == 'POST' and add_user_form.validate_on_submit():
        if add_user_form.status.data == 'True':
            status = True
        else:
            status = False
        u = User(username=add_user_form.username.data.strip(), email=add_user_form.email.data.strip(),
                 role=add_user_form.role.data, status=status, password='123456')
        db.session.add(u)
        flash({'success': '添加用户<%s>成功！' % add_user_form.username.data.strip()})
    if delete_user_form.validate_on_submit():
        u = User.query.get_or_404(int(delete_user_form.user_id.data.strip()))
        db.session.delete(u)
        flash({'success': '删除用户<%s>成功！' % u.username})

    users = User.query.all()

    return render_template('vip/users.html', users=users, addUserForm=add_user_form,
                           deleteUserForm=delete_user_form)



@vip.route('/password', methods=['GET', 'POST'])
@login_required
def password():
    change_password_form = ChangePasswordForm(prefix='change_password')
    if request.method == 'POST' and change_password_form.validate_on_submit():
        if current_user.verify_password(change_password_form.old_password.data.strip()):
            current_user.password = change_password_form.password.data.strip()
            # db.session.add(current_user)
            db.session.commit()
            flash({'success': '您的账户密码已修改成功！'})
        else:
            flash({'error': '无效的旧密码！'})

    return render_template('vip/password.html', changePasswordForm=change_password_form)


@vip.route('/draw_preview', methods=['GET'])
@login_required
def draw_preview():
    width = request.args.get('width', type=int, default=800)
    height = request.args.get('height', type=int, default=400)
    background_color = request.args.get('background_color', '#424155')
    title = request.args.get('title', '何三笔记')
    title_color = request.args.get('title_color', '#ff0000')
    print(title_color)
    title_size = request.args.get('title_size', type=int, default=60)
    font_path = os.path.join(admin.static_folder, 'fonts', '站酷庆科黄油体.ttf')
    d_config = {
        'width': width,
        'height': height,
        'background_img': '',
        'background_color': background_color,

        'layers': [
            {
                'layer_type': 'text',
                'color': title_color,
                'font': {
                    'font': font_path,
                    'size': title_size,
                },
                'position': '0,0',
                'align': 'center',
                'text': title
            }
        ]
    }
    d = util.H3blogDrow()
    d.parse_config(d_config)
    img = d.draw()
    bytesIO = io.BytesIO()
    img.save(bytesIO, 'PNG')
    bytesIO.seek(0)
    return send_file(bytesIO, mimetype='image/png')


@vip.route('/upload', methods=['POST'])
@login_required
def upload():
    """图片上传处理"""
    file = request.files.get('file')
    if not allowed_file(file.filename):
        res = {
            'code': 0,
            'msg': '图片格式异常'
        }
    else:
        url_path = ''
        upload_type = current_app.config.get('H3BLOG_UPLOAD_TYPE')
        ex = os.path.splitext(file.filename)[1]
        filename = datetime.now().strftime('%Y%m%d%H%M%S') + ex
        if upload_type is None or upload_type == '' or upload_type == 'local':
            file.save(os.path.join(current_app.config['H3BLOG_UPLOAD_PATH'], filename))
            url_path = url_for('admin.get_image', filename=filename)
        elif upload_type == 'qiniu':
            try:
                qiniu_cdn_url = current_app.config.get('QINIU_CDN_URL')
                url_path = qiniu_cdn_url + upload_file_qiniu(file.read(), filename)
            except Exception as e:
                return jsonify({'success': 0, 'message': '上传图片异常'})
        # 返回
        pic = Picture(name=file.filename if len(file.filename) < 32 else filename, url=url_path)
        db.session.add(pic)
        res = {
            'code': 1,
            'msg': u'图片上传成功',
            'url': url_path
        }
    return jsonify(res)


@vip.route('/tags')
@login_required
def tags():
    '''
    标签管理
    '''
    name = request.values.get('name', '')
    page = request.args.get('page', 1, type=int)
    tags = Tag.query.filter(
        Tag.name.like("%" + name + "%") if name is not None else ''
    ).order_by(Tag.id.asc()). \
        paginate(page, per_page=current_app.config['H3BLOG_POST_PER_PAGE'], error_out=False)
    return render_template('vip/tags.html', tags=tags, name=name)


@vip.route('/tags/add', methods=['GET', 'POST'])
@login_required
def tag_add():
    """
    添加标签
    """
    form = CategoryForm()
    if request.method == 'POST' and form.validate_on_submit():
        Tag.add(form.name.data.strip())
        return redirect(url_for('vip.tags'))

    return render_template('vip/tag.html', form=form)


@vip.route('/tags/edit', methods=['GET', 'POST'])
@login_required
def tag_edit():
    """
    修改标签
    """
    id = request.values.get('id', 0, type=int)
    c = Tag.query.get(id)
    form = TagForm()
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(c)
        db.session.commit()
        return redirect(url_for('vip.tags'))

    form = TagForm(obj=c)
    return render_template('vip/tag.html', form=form)


@vip.route('/categorys', methods=['GET'])
@login_required
def categorys():
    """
    分类
    """
    page = request.args.get('page', 1, type=int)
    categorys = Category.query.order_by(Category.visible.desc(), Category.sn.asc()).paginate(page, per_page=
    current_app.config['H3BLOG_POST_PER_PAGE'], error_out=False)

    return render_template('vip/categorys.html', categorys=categorys)


@vip.route('/categorys/add', methods=['GET', 'POST'])
@login_required
def categroy_add():
    """
    添加分类
    """
    form = CategoryForm()
    if request.method == 'POST' and form.validate_on_submit():
        c = Category()
        form.populate_obj(c)
        # c = Category(title=form.title.data.strip(),
        #         name=form.name.data.strip(),
        #         desp = form.desp.data,
        #         tpl_mold = form.tpl_mold.data,
        #         tpl_list = form.tpl_list.data.strip(),
        #         tpl_page = form.tpl_page.data.strip(),
        #         content = form.content.data,
        #         seo_title = form.seo_title.data,
        #         seo_description = form.seo_description.data,
        #         seo_keywords = form.seo_keywords.data)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('vip.categorys'))

    return render_template('vip/category.html', form=form)


@vip.route('/categorys/edit/<id>', methods=['GET', 'POST'])
@login_required
def categroy_edit(id):
    """
    修改分类
    """
    c = Category.query.get(id)
    form = CategoryForm()
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(c)
        db.session.commit()
        return redirect(url_for('vip.categorys'))

    form = CategoryForm(obj=c)
    return render_template('vip/category.html', form=form)


@vip.route('/uploads/<path:filename>')
def get_image(filename):
    return send_from_directory(current_app.config['H3BLOG_UPLOAD_PATH'], filename)


@vip.route('/imagehosting')
@login_required
def image_hosting():
    """
    图床
    """
    # from app.util import file_list_qiniu
    # imgs = file_list_qiniu()
    page = request.args.get('page', 1, type=int)
    imgs = Picture.query.order_by(Picture.id.desc()). \
        paginate(page, per_page=20, error_out=False)
    return render_template('vip/image_hosting.html', imgs=imgs)


@vip.route('/baidu_push_urls', methods=['POST'])
def baidu_push_article():
    urls = request.form.get('urls')
    domain = current_app.config.get('H3BLOG_DOMAIN', 'https://www.h3blog.com')
    ret = baidu_push_urls(domain, urls)
    return jsonify(ret)


@vip.route('/import_article', methods=['POST'])
def import_article():
    from readability import Document
    url = request.form.get('url')
    download_img = request.form.get('download_img', 0, type=int)
    is_download_img = True if download_img == 1 else False
    req_html = request.form.get('html')
    if req_html and len(req_html) > 0:
        html = req_html
    else:
        html = util.open_url(url)
        html = util.strdecode(html)

        doc = Document(html)
        html = doc.summary()
    markdown = util.html2markdown(html, url, is_download_img, '')
    return jsonify(markdown)


def recommends():
    '''
    推荐列表
    '''
    page = request.args.get('page', 1, type=int)
    recommends = Recommend.query.order_by(Recommend.sn.desc()). \
        paginate(page, per_page=current_app.config['H3BLOG_POST_PER_PAGE'], error_out=False)
    return render_template('vip/recommends.html', recommends=recommends)


@vip.route('/recommends/add', methods=['GET', 'POST'])
@login_required
def recommends_add():
    '''
    添加推荐
    '''
    form = RecommendForm()
    if request.method == 'POST' and form.validate_on_submit():
        r = Recommend(title=form.title.data.strip(),
                      url=form.url.data,
                      img=form.img.data,
                      sn=form.sn.data,
                      state=form.state.data)
        db.session.add(r)
        db.session.commit()
        return redirect(url_for('vip.recommends'))

    return render_template('vip/recommend.html', form=form)


@vip.route('/recommends/edit/<id>', methods=['GET', 'POST'])
@login_required
def recommends_edit(id):
    """
    修改推荐
    """
    r = Recommend.query.get(id)
    form = RecommendForm()
    if request.method == 'POST' and form.validate_on_submit():
        r.title = form.title.data.strip()
        r.url = form.url.data
        r.img = form.img.data
        r.sn = form.sn.data
        r.state = form.state.data
        db.session.commit()
        return redirect(url_for('vip.recommends'))

    form = RecommendForm(obj=r)
    return render_template('vip/recommend.html', form=form)


@vip.route('/accesslogs', methods=['GET'])
@login_required
def access_logs():
    '''
    搜索引擎抓取记录
    '''
    remark = request.args.get('remark', '')
    params = {'remark': remark}
    page = request.args.get('page', 1, type=int)
    logs = AccessLog.query.filter(
        AccessLog.remark.like("%" + remark + "%") if remark is not None else ''
    ).order_by(AccessLog.timestamp.desc()). \
        paginate(page, per_page=current_app.config['H3BLOG_POST_PER_PAGE'], error_out=False)
    return render_template('vip/access_log.html', logs=logs, params=params)


@vip.route('/invitcodes', methods=['GET', 'POST'])
@login_required
def invit_codes():
    '''
    邀请码
    '''
    form = InvitcodeForm()
    if request.method == 'POST' and form.validate_on_submit:
        count = int(form.count.data)
        cs = gen_invit_code(count, 15)
        for c in cs:
            ic = InvitationCode(code=c)
            db.session.add(ic)
        db.session.commit()
    page = request.args.get('page', 1, type=int)
    codes = InvitationCode.query.order_by(InvitationCode.id.asc()). \
        paginate(page, per_page=current_app.config['H3BLOG_POST_PER_PAGE'], error_out=False)

    return render_template('vip/invit_codes.html', codes=codes, form=form)



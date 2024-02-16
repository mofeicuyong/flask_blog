from flask import url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, HiddenField, BooleanField, SubmitField, SelectField, \
    TextAreaField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User, Category, Article
from datetime import datetime
import os


class ConfigForm(FlaskForm):
    uri = StringField('数据库地址', validators=[DataRequired])
    submit = SubmitField('下一步')


class LoginForm(FlaskForm):
    username = StringField('帐号', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField(label='记住我', default=False)
    submit = SubmitField('登 录')


class AddAdminForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 16, message='用户名长度要在1和16之间')])
    email = StringField('邮箱', validators=[DataRequired(), Length(6, 64, message='邮件长度要在6和64之间'),
                                          Email(message='邮件格式不正确！')])
    password = PasswordField('密码', validators=[DataRequired(), EqualTo('password2', message='密码必须一致！')])
    password2 = PasswordField('重输密码', validators=[DataRequired()])
    submit = SubmitField('注 册')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已被注册！')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已被注册！')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('旧密码', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired(), EqualTo('password2', message='密码必须一致！')])
    password2 = PasswordField('重输密码', validators=[DataRequired()])
    submit = SubmitField('更新密码')


class AddUserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64, message='姓名长度要在1和64之间')])
    email = StringField('邮箱', validators=[DataRequired(), Length(6, 64, message='邮件长度要在6和64之间'),
                                          Email(message='邮件格式不正确！')])
    role = SelectField('权限', choices=[('1', '管理员'), ('2', '一般用户'), ('3', 'vip')])
    status = SelectField('状态', choices=[('True', '正常'), ('False', '注销')])
    submit = SubmitField('添加用户')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已被注册！')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已被注册！')


class DeleteUserForm(FlaskForm):
    user_id = StringField(validators=[DataRequired()])


class EditUserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64, message='姓名长度要在1和64之间')])
    email = StringField('邮箱', validators=[DataRequired(), Length(6, 64, message='邮件长度要在6和64之间'),
                                          Email(message='邮件格式不正确！')])
    role = SelectField('权限', choices=[('1', '管理员'), ('0', '一般用户'), ('3', 'vip用户')])
    status = SelectField('状态', choices=[('True', '正常'), ('False', '注销')])
    submit = SubmitField('修改用户')
class DeleteArticleForm(FlaskForm):
    article_id = StringField(validators=[DataRequired()])

class ArticleForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('标题', validators=[DataRequired('请录入标题')])
    name = StringField('标识名称', render_kw={'placeholder': '自定义路径'})
    content = TextAreaField('文章内容')
    content_html = TextAreaField('文章内容')
    editor = HiddenField('编辑器', default='')
    category_id = SelectField('分类', coerce=int, default=1, validators=[DataRequired('请选择分类')])
    tags = StringField('标签', render_kw={'data-role': 'tagsinput'})
    state = HiddenField('状态', default=0)
    thumbnail = HiddenField('缩略图', default='/static/img/thumbnail.jpg')
    summary = TextAreaField('概述', validators=[Length(0, 300, message='长度必须设置在300个字符内')])
    timestamp = DateTimeField('发布时间', default=datetime.now)
    h_content = TextAreaField('隐藏内容', default='')
    h_role = SelectField('角色可见', choices=[('1', '管理员'), ('0', '一般用户'), ('3', 'vip用户')])
    save = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(ArticleForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(category.id, category.title)
                                    for category in
                                    Category.query.filter(Category.tpl_mold == 'list').order_by(Category.title).all()]

    def validate_name(self, field):
        """
        验证文章名称标识的唯一性
        """
        name = field.data
        articles = Article.query.filter_by(name=name).all()
        if len(articles) > 1:
            raise ValidationError('路径已经存在')
        if len(articles) == 1 and self.id.data and articles[0].id != int(self.id.data):
            raise ValidationError('路径已经存在')


class CategoryForm(FlaskForm):
    # id = HiddenField('id')
    title = StringField('名称', validators=[DataRequired()])
    name = StringField('标识', validators=[DataRequired()])
    desp = TextAreaField('描述')
    tpl_mold = SelectField('类型', choices=[('list', '列表模板'), ('single_page', '单页模板')])
    tpl_list = SelectField('类型', default='category.html')
    tpl_page = SelectField('详情模板', default='article.html')
    content = TextAreaField('内容')
    seo_title = StringField('SEO标题')
    seo_keywords = StringField('SEO关键词')
    seo_description = TextAreaField('SEO描述')
    sn = StringField('排序', default=0)
    visible = BooleanField('显示', default=True)
    icon = StringField('图标')
    submit = SubmitField('提交')

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        base_path = os.path.join(os.getcwd(), 'app', 'main', 'themes', 'tend')
        tpls = [(t, t) for t in os.listdir(base_path)]
        self.tpl_list.choices = tpls
        self.tpl_page.choices = tpls


class TagForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('标识', validators=[DataRequired()])
    visible = BooleanField('显示', default=True)
    submit = SubmitField('提交')


class RecommendForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('标题', validators=[DataRequired()])
    url = StringField('链接', validators=[DataRequired()], default='#')
    sn = IntegerField('排序', default=0)
    img = StringField('图片', validators=[DataRequired()])
    state = SelectField('状态', choices=[('1', '正常'), ('0', '停止')])
    submit = SubmitField('提交')


class OnlineToolForm(FlaskForm):
    id = HiddenField('id')
    title = StringField('标题', validators=[DataRequired()])
    desp = StringField('描述', validators=[DataRequired()])
    url = StringField('链接', validators=[DataRequired()], default='#')
    sn = IntegerField('排序', default=0)
    img = StringField('图片', validators=[DataRequired()])
    state = SelectField('状态', choices=[('1', '正常'), ('0', '停止')])
    submit = SubmitField('提交')


class InvitcodeForm(FlaskForm):
    count = IntegerField('数量', default=0, validators=[DataRequired()])
    submit = SubmitField('提交')


class BaidutongjiForm(FlaskForm):
    token = StringField('健值')
    status = SelectField('状态', choices=[('True', '启用'), ('False', '停用')])
    submit = SubmitField('提交')


class SettingForm(FlaskForm):
    h3blog_domain = StringField('网站域名', default='暂无', validators=[DataRequired()])
    h3blog_title = StringField('网站名称', default='虚假真白萌', validators=[DataRequired()])
    h3blog_keywords = StringField('关键字', default='小说漫画')
    h3blog_description = TextAreaField('网站描述')

    h3blog_comment = BooleanField(label='开启评论', default=False)
    h3blog_register_invitecode = BooleanField(label='开启邀请注册', default=False)
    h3blog_editor = SelectField('默认编辑器', choices=[('markdown', 'markdown'), ('tinymce', 'tinymce')], default='markdown')
    h3blog_template = SelectField('模板')

    h3blog_upload_type = SelectField('图片存储方式', choices=[('local', '本地'), ('qiniu', '七牛云')])
    h3blog_allowed_image_extensions = StringField('运行图片后缀', default='png, jpg, jpeg, gif, webp')

    submit = SubmitField('提交')

    def __init__(self, *args, **kwargs):
        super(SettingForm, self).__init__(*args, **kwargs)
        base_path = os.path.join(os.getcwd(), 'app', 'main', 'themes')
        tpls = [(t, t) for t in os.listdir(base_path)]
        self.h3blog_template.choices = tpls

    def to_dict(self):
        '''转换成map'''
        ret = {}
        for name in self._fields:
            if name in ['csrf_token', 'submit']:
                continue
            ret[name] = self._fields[name].data
        return ret


class AddFolderForm(FlaskForm):
    directory = StringField('文件夹')
    submit = SubmitField('确定')




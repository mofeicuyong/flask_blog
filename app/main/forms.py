# -*- coding:utf-8 -*-


from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User, InvitationCode


class LoginForm(FlaskForm):
    username = StringField('帐号', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField(label='记住我', default=False)
    submit = SubmitField('登 录')


class RegistForm(FlaskForm):
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


class InviteRegistForm(RegistForm):
    code = StringField('邀请码')

    def validate_code(self, field):
        if field.data.strip()!='':
            ic = InvitationCode.query.filter(InvitationCode.code == field.data.strip()).first()
            if ic is None:
                raise ValidationError('无效邀请码')
            if not ic.state:
                raise ValidationError('邀请码已使用')


class PasswordForm(FlaskForm):
    pwd = PasswordField('当前密码', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired(), EqualTo('password2', message='密码必须一致！')])
    password2 = PasswordField('重输密码', validators=[DataRequired()])
    email = StringField('新邮箱',validators=[DataRequired()])
    submit = SubmitField('修改密码')

    def validate_pwd(self, field):
        if not current_user.verify_password(field.data):
            raise ValidationError('当前密码不正确')


class SearchForm(FlaskForm):
    search = StringField('search', validators=[DataRequired(), Length(1, 64, message='搜索内容不能超过64个字符')])


class CommentForm(FlaskForm):
    article_id = IntegerField('文章', validators=[DataRequired()])
    reply_id = IntegerField('回复评论', default=0)
    content = StringField('评论', validators=[DataRequired()])

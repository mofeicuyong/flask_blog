from flask import Blueprint

vip = Blueprint('vip', __name__, template_folder="templates", static_url_path='/statics', static_folder='static')

# 在末尾导入相关模块，是为了避免循环导入依赖，因为在下面的模块中还要导入蓝本main
from . import views, errors

from threading import active_count
from typing import Any, List
from flask import Flask
from flask_login import current_user
from flask import url_for, request 
from app.models import Article,  Tag, Category, article_tag, Recommend, User, \
     InvitationCode,  Comment
import re

def register_template_filter(app):
    '''注册模板过滤器'''

    @app.template_filter('hidden_content')
    def hidden_content(content):
        if current_user.is_authenticated:
            return content.replace('[h3_hidden]','').replace('[/h3_hidden]','')
        else:
            login_url = url_for('main.login') + '?next=' + request.path
            repl = '''
            <p class="border border-warning p-2 text-center">
            本文隐藏内容 <a href="{}">登陆</a> 后才可以浏览
            </p>
            '''.format(login_url)
            return re.sub('\[h3_hidden\].*?\[/h3_hidden\]',repl,content,flags=re.DOTALL)

def register_template_global(app: Flask):
    """
    注册模板全局函数
    """
    @app.template_global()
    def get_articles(
            categorys:str = None, #文章分类，分类标识逗号分割比如"python,flask,django"
            tags:str = None, # 文章标签，文章标签逗号分割比如"python,安全,何三笔记"
            is_hot:bool = False, # 是否热门文章,根据浏览量进行获取
            hot_num:int = 0, # 热门文章值，比如 hot_num = 5 是获取文章浏览量大于等于5的数据
            orderby:str = '', # 排序 按照发布时间 asc=升序 desc= 降序
            is_page:bool = False, # 是否分页，如果is_page=True即开启分页,如果开启分页返回数据将是Paginate类型
            page:int = 1,  # 分页页数
            per_page:int = 10 # 每页条数
        ) -> Any:
        """
        根据条件获取已发布的文章
        """
        results = []
        query = Article.query.filter(Article.state == 1)
        if categorys and len(categorys) > 0:
            query = query.filter(Article.category.has(Category.name.in_(categorys.split(','))))
        if tags and len(tags) > 0:
            query = query.filter(Article.tags.any(Tag.name.in_(tags.split(','))))
        if is_hot:
            query = query.filter(Article.vc >= hot_num)
            query = query.order_by(Article.vc.desc())
        if orderby.lower() == 'asc':
            query = query.order_by(Article.timestamp.asc())
        elif orderby.lower() == 'desc':
            query = query.order_by(Article.timestamp.desc())
        else:
            query = query.order_by(Article.timestamp.desc())
        if is_page:
            if type(page) != int:
                try:
                    page = int(page)
                except:
                    page = 1
            results = query.paginate(page, per_page = per_page, error_out = False)
        else:
            results = query.all()
        return results

    @app.template_global()
    def get_categorys(names:str = None, visible = None) -> List[Category] :
        """
        获取文章分类
        """
        query = Category.query
        if names and len(names) > 0:
            query = query.filter(Category.name.in_(names.split(',')))
        if visible:
            query = query.filter(Category.visible == visible)
        query = query.order_by(Category.sn.asc())
        return query.all()
    
    @app.template_global()
    def get_tags(tags:str = None) -> List[Tag] :
        """
        获取系统标签
        """
        query = Tag.query.filter(Tag.visible == True)
        if tags and len(tags) > 0:
            query = query.filter(Tag.name.in_(tags.split(',')))
        return query.all()
    
    



if __name__ == '__main__':
    content = '''
    我是中国人1
    我是中国人2
    我是中国人3
    [hidden]
    我是中国人4
    我是中国人5
    [/hidden]
    '''
    m_tr =  re.findall('\[hidden\].*?\[/hidden\]',content,re.DOTALL)
    print(m_tr)
    m_tr = re.sub('\[hidden\].*?\[/hidden\]','我爱你',content,flags=re.DOTALL)
    print(m_tr)
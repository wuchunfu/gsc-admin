# coding=utf-8
import flask_login as login
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
from wtforms import fields

from datetime import datetime

from snow.ext import db, redis

from snow.models.question import Question

CATEGORY = [(1, '财经'), (2, '百科'), (3, '历史'), (4, '地理'), (5, '诗词')]

LEVEL = [(1, '简单'), (2, '中等'), (3, '困难')]

STATUS = [(1, '正常'), (0, '删除')]

SERIAL = ['A', 'B', 'C', 'D']


class QuestionView(ModelView):

    page_size = 12

    def is_accessible(self):
        return login.current_user.is_authenticated and (login.current_user.role & 8)

    @property
    def can_create(self):
        return self.is_accessible() and (login.current_user.role & 16)

    @property
    def can_edit(self):
        return self.is_accessible() and (login.current_user.role & 32)

    @property
    def can_delete(self):
        return self.is_accessible() and (login.current_user.role & 64)

    column_sortable_list = ('id_', )

    column_labels = {
        'id_': 'ID',
        'content': '题目',
        'options': '选项',
        'answer': '答案',
        'level': '难度',
        'category': '分类',
        'status': '状态',
        'create_time': '创建时间',
        'update_time': '更新时间',
    }

    column_list = ('id_', 'content', 'options', 'answer', 'level', 'category', 'status', 'update_time')

    form_columns = ('content', 'options', 'answer', 'level', 'category', 'status')
    can_view_details = True

    column_choices = {
        'level': LEVEL,
        'status': STATUS,
        'category': CATEGORY,
    }

    def _render_content(self, context, model, name):
        if '###' in model.content:
            content, image = model.content.split('###')
            return Markup('<span>{}</span><br><image src="{}" style="width:100px;"/>'.format(content, image))
        return model.content

    def _render_options(self, context, model, name):
        options = model.options.split('|')
        s = ''
        if 'https://' in model.options:
            for x in enumerate(options):
                s += '{}、<image src="{}" style="width:100px;"/><br><br>'.format(SERIAL[x[0]], x[1])
            return Markup(s)
        for x, y in enumerate(options):
            s += SERIAL[x] + '、' + y + '<br>'
        return Markup(s)

    column_formatters = {
        'content': _render_content,
        'options': _render_options,
        'answer': lambda a, b, c, d: SERIAL[c.answer - 1],
    }

    form_extra_fields = {
        'options': fields.StringField(label='选项', default='', description='多个选项以`|`隔开'),
        'level': fields.SelectField(label='难度', choices=LEVEL, default=1),
        'status': fields.SelectField(label='状态', choices=STATUS, default=1),
        'category': fields.SelectField(label='分类', choices=CATEGORY, default=2),
    }

    column_filters = ('content', 'id_', 'options', 'level', 'category', 'status')

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.create_time = datetime.now()
            model.update_time = model.create_time
        else:
            model.update_time = datetime.now()
        model.content = form.data['content'].strip().replace(' ', '')
        model.options = form.data['options'].strip().replace(' ', '').replace('｜', '|')
        return super(QuestionView, self).on_model_change(form, model, is_created)

    def after_model_change(self, form, model, is_created):
        redis.delete('question:{}'.format(model.id_))
        return super(QuestionView, self).after_model_change(form, model, is_created)


category = '百科知识'

question_view = QuestionView(Question, db.session, name='题目列表', category=category)

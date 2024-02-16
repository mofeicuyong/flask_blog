from flask import request
def get_obj_fields(obj):
    """获取模型对象的表字段, obj或model均可"""
    if obj is None:
        return []
    return [column.name for column in obj.__table__.columns]


def request_form_auto_fill(model) -> None:
    data = request.form.to_dict()
    if data is not None:
        data = {key: value for key, value in data.items()
                if key in get_obj_fields(model)}
        [setattr(model, key, value) for key, value in data.items()]

def get_request_valid_data(obj):
    data = request.get_json()
    if data is not None:
        data = {key: value for key, value in request.get_json().items()
                if key in get_obj_fields(obj)}
    return data
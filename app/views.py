from sqlalchemy import text
from flask import render_template, request

from app import app, db


def search_child(sql):
    result = db.engine.execute(sql)
    return [{'id': row[0], 'parent_id': row[1], 'name': row[2]}for row in result]


@app.route('/')
@app.route('/index', methods=['GET'])
def index():
    detail = ''
    try:
        search_id = int(request.args.get('search_id', None))
    except (TypeError, ValueError):
        search_id = None
        detail = f'Ошибка:Укажите число'

    if search_id:
        detail = f'Вы выбрали: {search_id}'
        sql = text(f'''SELECT * FROM tree WHERE id = {search_id}''')
    else:
        sql = text('SELECT * FROM tree')

    row_list = search_child(sql)
    if row_list:
        if row_list[0]['parent_id']:
            sql = text(f'''SELECT * FROM tree WHERE parent_id = {row_list[0]['parent_id']} UNION
                           SELECT * FROM tree WHERE id = {row_list[0]['parent_id']}''')
            row_list = search_child(sql)

    return render_template("index.html", title='Tree', rows=row_list, detail=detail, search_id=search_id if search_id else 1)

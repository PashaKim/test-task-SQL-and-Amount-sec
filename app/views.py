import redis
from datetime import datetime
from sqlalchemy import text
from flask import render_template, request, jsonify

from app import app, db


def search_child(sql):
    result = db.engine.execute(sql)
    return [{'id': row[0], 'parent_id': row[1], 'name': row[2]}for row in result]


@app.route('/', methods=['GET'])
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


def amount_time_check(amount, time_amount_d, seconds):
    start_time_key = ('%s_start_time' % seconds).encode()
    amount_key = ('%s_amount' % seconds).encode()
    error = error_detail = False

    timestamp_now = int(datetime.now().timestamp())
    amount_limit = app.config['AMOUNT_LIMITS_CONFIG'][seconds]

    time_amount_d[start_time_key] = int(time_amount_d[start_time_key])
    time_amount_d[amount_key] = int(time_amount_d[amount_key])

    if timestamp_now > time_amount_d[start_time_key] + seconds:
        time_amount_d[start_time_key] = timestamp_now
        time_amount_d[amount_key] = amount
    else:
        if time_amount_d[amount_key] + amount < amount_limit:
            time_amount_d[amount_key] += amount
        else:
            error = True
            error_detail = {'seconds': seconds, 'amount_limit': amount_limit}

    return error, error_detail, time_amount_d


@app.route('/request/<amount>', methods=['GET'])
def get_amount(amount):
    amount = int(amount)
    error_main = {'exaggerated': False}

    conn = redis.Redis('localhost')
    time_amount_d = conn.hgetall("time_amount_d")

    if not time_amount_d:  # Create first dict
        timestamp_now = int(datetime.now().timestamp())
        time_amount_d = dict()
        for seconds in list(app.config['AMOUNT_LIMITS_CONFIG'].keys()):
            time_amount_d[('%s_amount' % seconds).encode()] = 0
            time_amount_d[('%s_start_time' % seconds).encode()] = timestamp_now

        conn.hmset("time_amount_d", time_amount_d)

    for seconds in list(app.config['AMOUNT_LIMITS_CONFIG'].keys()):
        error, error_detail, time_amount_d = amount_time_check(amount, time_amount_d, seconds)
        if error:
            error_main = {'exaggerated': True, 'd': error_detail}
            break

    conn.hmset("time_amount_d", time_amount_d)
    # conn.flushall()
    response_d = {"error": f"amount limit exeeded ({error_main['d']['amount_limit']}"
                           f"/{error_main['d']['seconds']}sec)"} if error_main['exaggerated'] else {"result": "OK"}
    return jsonify(response_d)

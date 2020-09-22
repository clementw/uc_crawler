import json
import re

import dateutil


def empty_list(lst):
    if lst:
        return int(lst[0])
    else:
        return 0


def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def format_time(time_str):
    h = re.findall(r"(\d+)时", time_str)
    m = re.findall(r"(\d+)分", time_str)
    s = re.findall(r"(\d+)秒", time_str)

    h = empty_list(h)
    m = empty_list(m)
    s = empty_list(s)

    total_s = 3600 * h + 60 * m + s
    return total_s


def gen_date_int(lst):
    date_ints = []
    for day in lst:
        date_ints.append(dateutil.parser.parse(day))
    return set([d.toordinal() for d in date_ints])


def add_call_detail(d1, d2):
    d1['talk_seconds'] += d2[3]
    d1['talk_cnt'] += 1
    if d2[4] == '被叫':
        d1['called_cnt'] += 1
        d1['called_seconds'] += d2[3]
    elif d2[4] == '主叫':
        d1['call_cnt'] += 1
        d1['call_seconds'] += d2[3]


def add_msg_detail(d1, d2):
    d1['msg_cnt'] += 1
    if d2[2] == '发送':
        d1['send_cnt'] += 1
    elif d2[2] == '接收':
        d1['receive_cnt'] += 1


def load_json(filename):
    with open('json/'+filename) as data:
        return json.load(data)


def dump_json(filename, var):
    with open('json/'+filename, 'w') as f:
        json.dump(var, f)

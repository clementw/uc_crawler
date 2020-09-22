import calendar
import collections
import datetime
import operator
import os

import dateutil
import xlrd
from dateutil import relativedelta, parser

from helper import time_in_range, format_time, gen_date_int, \
    add_call_detail, add_msg_detail, load_json, dump_json

province_dict = {'北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽',
                 '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃',
                 '青海', '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'}


class ExcelProcessing:
    def __init__(self):
        cwd = os.getcwd()
        self.call_list = []
        self.msg_list = []
        for file in os.listdir(cwd+'/excel'):
            def open_excel(ending, dict_name):
                if file.endswith(ending):
                    wb = xlrd.open_workbook('excel/'+file)
                    sh = wb.sheet_by_index(0)
                    for rownum in reversed(range(1, wb.sheet_by_index(0).nrows)):
                        dict_name.append(sh.row_values(rownum))

            open_excel('通信.xls', self.call_list)
            open_excel('彩信.xls', self.msg_list)
        self.phone_list = set()
        self.msg_phone_list = set()
        phone_location = {}
        for call in self.call_list:
            # convert to seconds
            call[3] = format_time(call[3])
            self.phone_list.add(call[5])
            phone_location[call[5]] = call[7]
        for msg in self.msg_list:
            self.msg_phone_list.add(msg[3])

        self.month_list = []
        first = datetime.date.today().replace(day=1)
        i = 6

        while i > 0:
            self.month_list.append(first)
            first -= dateutil.relativedelta.relativedelta(months=1)
            i -= 1

        # msg location
        for msg in self.msg_list:
            # same number
            if msg[3] in phone_location:
                msg.append(phone_location[msg[3]])
            else:
                msg.append('')

    # call[3] time, call[5] number, call[4] type

    def total_time_rank(self):
        ranked_list = []

        def search(phone):
            for item in ranked_list:
                if item['phone'] == phone:
                    return False
            return True

        for call in self.call_list:
            if search(call[5]):
                ranked_list.append({'phone': call[5], 'talkMinutes': 0,
                                    'callCnt': 0, 'calledCnt': 0, 'phoneLocation': call[7], 'identical': False,
                                    'phoneInfo': '未知', 'phoneLabel': '未知'})

            for number in ranked_list:
                if number['phone'] == call[5]:
                    number['talkMinutes'] += call[3]
                if call[4] == '被叫':
                    number['calledCnt'] += 1
                elif call[4] == '主叫':
                    number['callCnt'] += 1

        # sort by minutes
        ranked_list.sort(key=lambda k: k['talkMinutes'], reverse=True)

        # total minutes
        for number in ranked_list:
            number['talkMinutes'] = round(number['talkMinutes'] / 60, 2)

        dump_json('total_time_rank.json', ranked_list)

    def user_portrait(self):
        user_portrait = {'active_days': {'end_day': '', 'start_day': '', 'stop_3_days': 0, 'stop_3_days_detail': [],
                                         'stop_days': 0, 'stop_days_detail': [], 'total_days': 0}, 'both_call_cnt': 0,
                         'content_distribution': {}, 'night_activity_ratio': 0.00,
                         'night_msg_ratio': 0}
        date_list = []
        total_date_list = []
        call_hour_list = []
        msg_hour_list = []
        location_list = []
        call_status = {}

        for call in self.call_list:
            date_list.append(call[2][:-9])
            call_hour_list.append(int(call[2][11:13]))
            location_list.append(call[7])

        for msg in self.msg_list:
            msg_hour_list.append(int(msg[0][11:13]))

        prov_counter = collections.Counter(location_list)
        mc = prov_counter.most_common(1)[0]
        user_portrait['content_distribution'] = {'location': mc[0],
                                                 'ratio': round(mc[1] * 100 / len(self.call_list), 2)}

        date_list.sort()
        user_portrait['active_days']['end_day'] = date_list[-1]
        user_portrait['active_days']['start_day'] = date_list[0]

        for month in self.month_list:
            num_days = calendar.monthrange(month.year, month.month)[1]
            total_date_list.extend([datetime.date(month.year, month.month, day).strftime('%Y-%m-%d')
                                    for day in range(1, num_days + 1)])

        stop_days_detail = list(set(total_date_list) - set(date_list))
        stop_days_detail.sort()
        user_portrait['active_days']['stop_days_detail'] = stop_days_detail
        user_portrait['active_days']['stop_days'] = len(stop_days_detail)

        stop_date_ints = list(gen_date_int(stop_days_detail))
        # live_date_ints = list(gen_date_int(date_list))
        stop_3_days_detail = set()
        for date_int in stop_date_ints:
            if date_int + 1 and date_int + 2 in stop_date_ints:
                user_portrait['active_days']['stop_3_days'] += 1
                stop_3_days_detail.add(date_int)

        stop_3_days_detail = list(stop_3_days_detail)
        # stop_3_days_detail[-1] += 2
        for date_int in stop_3_days_detail:
            day = datetime.date.fromordinal(date_int)
            nextday = datetime.date.fromordinal(date_int + 2)
            user_portrait['active_days']['stop_3_days_detail'].append('{} - {}'.format(day, nextday))

        def hour_ratio(lst):
            hours = 0
            for hour in lst:
                if hour >= 23 or hour <= 5:
                    hours += 1
            return hours

        call_night_hours = hour_ratio(call_hour_list)
        msg_night_hours = hour_ratio(msg_hour_list)

        user_portrait['night_activity_ratio'] = round(call_night_hours * 100 / len(call_hour_list), 2)
        user_portrait['night_msg_ratio'] = round(msg_night_hours * 100 / len(msg_hour_list), 2)

        user_portrait['active_days']['total_days'] = dateutil.parser.parse(
            date_list[-1]).toordinal() - dateutil.parser.parse(date_list[0]).toordinal()

        for number in self.phone_list:
            call_status[number] = {'call': False, 'called': False}

        for call in call_status:
            for item in self.call_list:
                if call == item[5]:
                    if item[4] == '被叫':
                        call_status[call]['called'] = True
                    elif item[4] == '主叫':
                        call_status[call]['call'] = True

        for number in call_status:
            if call_status[number]['called'] is True and call_status[number]['call'] is True:
                user_portrait['both_call_cnt'] += 1

        dump_json('user_portrait.json', user_portrait)

    def special_cate(self):
        special_cate = []

        numtype = ['110', '120']
        for num in numtype:
            special_cate_dict = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0, "cate": num,
                                 "month_detail": [], "msg_cnt": 0, "phone_detail": [], "receive_cnt": 0, "send_cnt": 0,
                                 "talk_cnt": 0, "talk_seconds": 0, "unknown_cnt": 0}
            special_cate.append(special_cate_dict)

        def add_special_cate(typestr, index):
            for call in self.call_list:
                if call[5] == typestr:
                    special_cate[index]['talk_cnt'] += 1
                    if call[4] == '被叫':
                        special_cate[index]['calledCnt'] += 1
                        special_cate[index]['called_seconds'] += call[3]
                    elif call[4] == '主叫':
                        special_cate[index]['callCnt'] += 1
                        special_cate[index]['call_seconds'] += call[3]

        add_special_cate('110', 0)
        add_special_cate('120', 1)

        dump_json('special_cate.json', special_cate)

    def call_log(self):
        call_log = []
        call_detail_by_number = {}
        msg_detail_by_number = {}

        for number in self.phone_list:
            call_log_dict = {
                "call_cnt": 0,
                "call_seconds": 0,
                "called_cnt": 0,
                "called_seconds": 0,
                "contact_1m": 0,
                "contact_1w": 0,
                "contact_3m": 0,
                "contact_afternoon": 0,
                "contact_early_morning": 0,
                "contact_eveing": 0,
                "contact_morning": 0,
                "contact_night": 0,
                "contact_noon": 0,
                "contact_weekday": 0,
                "contact_weekend": 0,
                "detail": [],
                "first_contact_date": "",
                "last_contact_date": "",
                "msg_cnt": 0,
                "phone": "",
                "phone_info": "未知",
                "phone_label": "未知",
                "phone_location": "",
                "receive_cnt": 0,
                "send_cnt": 0,
                "talk_cnt": 0,
                "talk_seconds": 0,
                "unknown_cnt": 0
            }
            call_log_dict['phone'] = number
            call_detail_by_number[number] = []

            for call in self.call_list:
                if number == call[5]:
                    add_call_detail(call_log_dict, call)
                    call_detail_by_number[number].append(call)
                    call_log_dict['phone_location'] = call[7]

                    hour = int(call[2][11:13])
                    if time_in_range(23, 5, hour):
                        call_log_dict['contact_early_morning'] += 1
                    elif time_in_range(5, 9, hour):
                        call_log_dict['contact_morning'] += 1
                    elif time_in_range(9, 12, hour):
                        call_log_dict['contact_noon'] += 1
                    elif time_in_range(12, 18, hour):
                        call_log_dict['contact_afternoon'] += 1
                    elif time_in_range(18, 21, hour):
                        call_log_dict['contact_eveing'] += 1
                    elif time_in_range(21, 23, hour):
                        call_log_dict['contact_night'] += 1

            call_log.append(call_log_dict)

        for number in self.msg_phone_list:
            msg_detail_by_number[number] = []

        for msg in self.msg_list:
            for log in call_log:
                if msg[3] == log['phone']:
                    msg_detail_by_number[msg[3]] = msg
                    add_msg_detail(log, msg)

        for log in call_log:
            call_date = []
            for number in call_detail_by_number:
                if number == log['phone']:
                    log['first_contact_date'] = call_detail_by_number[number][0][2]
                    log['last_contact_date'] = call_detail_by_number[number][0][2]
                    for call in call_detail_by_number[number]:
                        day = dateutil.parser.parse(call[2][:-9])
                        weekday = day.weekday()
                        call_date.append(day.toordinal())
                        if 1 <= weekday <= 5:
                            log['contact_weekday'] += 1
                        elif 6 <= weekday <= 7:
                            log['contact_weekend'] += 1

            latest = call_date[-1]
            for day in call_date:
                if day >= latest - 7:
                    log['contact_1w'] += 1
                if day >= latest - 30:
                    log['contact_1m'] += 1
                if day >= latest - 90:
                    log['contact_3m'] += 1

        for number in call_detail_by_number:
            month_set = set()
            for call in call_detail_by_number[number]:
                month_set.add(call[2][:7])

            for log in call_log:
                if log['phone'] == number:
                    # add month detail
                    for month in month_set:
                        detail = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0, "month": '',
                                  "msg_cnt": 0, "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0, "talk_seconds": 0,
                                  "unknown_cnt": 0}
                        detail['month'] = month
                        log['detail'].append(detail)
                log['detail'].sort(key=operator.itemgetter('month'), reverse=True)

        for log in call_log:
            for detail in log['detail']:
                for number in call_detail_by_number:
                    for call in call_detail_by_number[number]:
                        if call[2][:7] == detail['month']:
                            add_call_detail(detail, call)
                    try:
                        for msg in msg_detail_by_number[number]:
                            if msg[0][:7] == detail['month']:
                                add_msg_detail(log, msg)
                    except KeyError:
                        pass

        call_log.sort(key=operator.itemgetter('talk_seconds'), reverse=True)
        dump_json('call_log.json', call_log)

    def monthly_consumption(self):
        monthly_consumption = []

        data = load_json('basic_info.json')

        money_spent = data['monthly_consumption']
        money_spent.insert(0, -1)
        for month in self.month_list:
            monthly_consumption_dict = {"call_cnt": 0, 'call_consumption': 0.00, "call_seconds": 0, "called_cnt": 0,
                                        "called_seconds": 0, "month": month.strftime('%Y-%m'), "msg_cnt": 0,
                                        "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0, "talk_seconds": 0,
                                        "unknown_cnt": 0}
            monthly_consumption.append(monthly_consumption_dict)

        i = 0
        for dict_ in monthly_consumption:
            dict_['call_consumption'] = money_spent[i]
            i += 1
            for call in self.call_list:
                if call[2][:7] == dict_['month']:
                    add_call_detail(dict_, call)
            for msg in self.msg_list:
                if msg[0][:7] == dict_['month']:
                    add_msg_detail(dict_, msg)

        data.pop('monthly_consumption')

        dump_json('basic_info.json', data)
        dump_json('monthly_consumption.json', monthly_consumption)

    def area_analysis(self):
        prov_set = set()
        area_analysis = []
        for call in self.call_list:
            for prov in province_dict:
                if prov in call[7]:
                    prov_set.add(prov)

        for prov in prov_set:
            area_analysis_dict = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0, "detail": [],
                                  "msg_cnt": 0, "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0, "talk_seconds": 0,
                                  "unknown_cnt": 0, 'area': prov}
            area_analysis.append(area_analysis_dict)

        for area in area_analysis:
            month_set = set()
            for call in self.call_list:
                if area['area'] in call[7]:
                    month_set.add(call[2][:7])
                    add_call_detail(area, call)
            for msg in self.msg_list:
                if area['area'] in msg[-1]:
                    add_msg_detail(area, msg)

            for month in month_set:
                detail = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0, "month": month,
                          "msg_cnt": 0, "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0, "talk_seconds": 0,
                          "unknown_cnt": 0}
                area['detail'].append(detail)

            area['detail'].sort(key=operator.itemgetter('month'), reverse=True)

            for detail in area['detail']:
                for call in self.call_list:
                    if detail['month'] == call[2][:7] and area['area'] in call[7]:
                        add_call_detail(detail, call)

                for msg in self.msg_list:
                    if msg[0][:7] == detail['month'] and area['area'] in msg[-1]:
                        add_msg_detail(area, msg)

        area_analysis.sort(key=operator.itemgetter('talk_seconds'), reverse=True)
        dump_json('area_analysis.json', area_analysis)

    def trip_analysis(self):
        gsd = load_json('basic_info.json')['phone_location']
        trip_analysis = []

        trip_location = set()
        calls_by_trip = {}
        for call in self.call_list:
            if gsd not in call[6]:
                trip_location.add(call[6])
                if call[6] not in calls_by_trip:
                    calls_by_trip[call[6]] = []
                else:
                    calls_by_trip[call[6]].append(call)

        msg_by_trip = {}
        for msg in self.msg_list:
            if gsd not in msg[-1] and msg[-1] != '':
                if msg[-1] not in msg_by_trip:
                    msg_by_trip[msg[-1]] = []
                else:
                    msg_by_trip[msg[-1]].append(msg)

        for location in trip_location:
            trip_analysis_dict = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0,
                                  "detail": [], "msg_cnt": 0, "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0,
                                  "talk_seconds": 0, "unknown_cnt": 0, 'date_distribution': [], 'location': location}
            trip_analysis.append(trip_analysis_dict)

        for trip in trip_analysis:
            for location in calls_by_trip:
                if trip['location'] == location:
                    date_distribution = set()
                    for call in calls_by_trip[location]:
                        date_distribution.add(call[2][:7])
                        add_call_detail(trip, call)
                    trip['date_distribution'] = list(date_distribution)
                    trip['date_distribution'].sort(reverse=True)
                    try:
                        for msg in msg_by_trip[location]:
                            add_msg_detail(trip, msg)
                    except KeyError:
                        pass

                    for month in trip['date_distribution']:
                        detail = {"call_cnt": 0, "call_seconds": 0, "called_cnt": 0, "called_seconds": 0,
                                  "month": month, "msg_cnt": 0, "receive_cnt": 0, "send_cnt": 0, "talk_cnt": 0,
                                  "talk_seconds": 0, "unknown_cnt": 0}
                        trip['detail'].append(detail)

                for detail in trip['detail']:
                    for call in calls_by_trip[location]:
                        if call[2][:7] == month:
                            add_call_detail(detail, call)
                    try:
                        for msg in msg_by_trip[location]:
                            add_msg_detail(detail, msg)
                    except KeyError:
                        pass

        dump_json('trip_analysis.json', trip_analysis)

    def head_info(self):
        head_info = {'user_type': 1}
        curr_time = datetime.datetime.now()
        head_info['report_time'] = str(curr_time)[:19]

        dump_json('head_info.json', head_info)

    def merge_json(self):
        main_data = {}

        t = {'trip_analysis': load_json('trip_analysis.json')}
        a = {'area_analysis': load_json('area_analysis.json')}
        b = {'basic_info': load_json('basic_info.json')}
        m = {'monthly_consumption': load_json('monthly_consumption.json')}
        u = {'user_portrait': load_json('user_portrait.json')}
        c = {'call_log': load_json('call_log.json')}
        h = {'head_info': load_json('head_info.json')}

        main_data.update(t)
        main_data.update(a)
        main_data.update(b)
        main_data.update(m)
        main_data.update(u)
        main_data.update(c)
        main_data.update(h)

        for name in main_data:
            os.remove('json/'+name+'.json')

        dump_json('main.json', main_data)

        print('数据分析完成')

    def full_run(self):
        self.call_log()
        self.area_analysis()
        self.trip_analysis()
        self.monthly_consumption()
        self.user_portrait()
        self.head_info()
        self.total_time_rank()
        self.merge_json()

import calendar
import json
import random
import string
import time
from datetime import datetime

import dateutil
import requests
from dateutil import parser

from helper import dump_json

unix_time = str(round(time.time() * 1000.0))
today = datetime.today()
today_str = today.strftime('%Y%m%d')

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
     "Chrome/58.0.3029.110 Safari/537.36"
callback_str = 'jQuery1720{}_{}'.format(''.join(random.choices(string.digits, k=18)), unix_time)

check_captcha = 'https://uac.10010.com/portal/Service/CheckNeedVerify?callback={}&userName={}&pwdType=01&_={}'

check_login = 'http://iservice.10010.com/e3/static/check/checklogin?_=' + unix_time
check_code_req = 'http://iservice.10010.com/e3/static/query/checkmapExtraParam?menuId={}&_={}'

# msg_detail = 'http://iservice.10010.com/e4/query/calls/call_sms-iframe.html?menuCode=000100030002'
callerLocationQuery = 'http://iservice.10010.com/e3/static/life/callerLocationQuery?_={}&number={}&checkCode=null'

account_history_url = 'http://iservice.10010.com/e4/query/basic/history_list.html?menuId=000100020001'
queryHistoryAccountMonth = 'http://iservice.10010.com/e3/static/query/queryHistoryAccount?_={}&accessURL={}' \
    .format(unix_time, account_history_url)

queryHistoryBill = 'http://iservice.10010.com/e3/static/query/queryHistoryBill?_={}&accessURL={}' \
                   '&querytype=0001&querycode=0001&billdate={}&flag=2'


def check_success(r):
    if json.loads(r.text)['isSuccess'] is False:
        print('网站繁忙，请稍后再试')


class UnicomCrawlerRequests:
    def __init__(self):
        self.phone = ''
        self.pwd = ''
        with requests.Session() as self.s:
            self.s.headers = {'User-Agent': ua}

        self.last_day = []
        self.last_day.append(today)
        month = datetime.today()
        month.replace(day=calendar.monthrange(month.year, month.month)[1])
        i = 5

        while i > 0:
            month = month.replace(day=calendar.monthrange(month.year, month.month)[1])
            month -= dateutil.relativedelta.relativedelta(months=1)
            self.last_day.append(month)
            i -= 1

    def login(self):
        login_url = 'https://uac.10010.com/portal/Service/MallLogin?redirectURL=http%3A%2F%2Fwww.10010.com&pwdType=01' \
                    '&productType=01&redirectType=01&rememberMe=1&callback={}&req_time={}&userName={}&password={}&_={}'
        self.s.get(check_captcha.format(callback_str, self.phone, unix_time))

        correct_input = False
        while correct_input is False:
            self.phone = input('输入手机号：')
            self.pwd = input('输入密码：')

            r = self.s.get(login_url.format(callback_str, unix_time, self.phone, self.pwd, unix_time))

            if '0000' in r.text:
                print('登录成功')
                correct_input = True
            else:
                print('手机号/密码错误，请重新输入')
                continue

    def basic_info(self):
        user_detail = 'http://iservice.10010.com/e3/static/query/searchPerInfoDetail/?_={}'.format(unix_time)

        account_balance_page = 'http://iservice.10010.com/e4/query/calls/account_balance.html?menuId=000100010013'
        account_balance = 'http://iservice.10010.com/e3/static/query/accountBalance/search?_={}' \
                          '&accessURL={}&type=onlyAccount'.format(unix_time, account_balance_page)

        basic_info = {'operator': "CHINAUNICOM", 'operator_zh': "中国联通", 'id_card_check': 0, 'name_check': 0,
                      'if_call_emergency1': 0, 'if_call_emergency2': 0, 'monthly_consumption': [], 'phone_location': '',
                      'phone': self.phone, 'ave_monthly_consumption': ''}

        self.s.post('http://iservice.10010.com/e3/static/common/info?_={}'.format(unix_time))

        r = self.s.post(check_login)
        d = json.loads(r.text)
        basic_info['id_card'] = d['userInfo']['certnum']
        basic_info['real_name'] = d['userInfo']['custName']
        print('获得姓名，身份证')

        r = self.s.post(user_detail)
        d = json.loads(r.text)
        reg_date = d['userInfo']['openDate']
        basic_info['reg_date'] = dateutil.parser.parse(reg_date).strftime('%Y-%m-%d')
        print('获得注册日期')

        r = self.s.post(callerLocationQuery.format(unix_time, self.phone))
        d = json.loads(r.text)
        if d['dto']['provinceName'] == d['dto']['cityName']:
            basic_info['phone_location'] = d['dto']['cityName']
        else:
            basic_info['phone_location'] = d['dto']['provinceName'] + d['dto']['cityName']
        print('获得归属地')

        r = self.s.post(account_balance)
        d = json.loads(r.text)
        basic_info['current_balance'] = d['acctbalance']
        print('获得余额')

        r = self.s.post(queryHistoryAccountMonth)
        d = json.loads(r.text)
        total = 0.00
        print('正在获取月消费')
        for dct in d['accountPeriod']:
            r = self.s.post(queryHistoryBill.format(unix_time, account_history_url, dct['queryDate']))
            try:
                spending = json.loads(r.text)['result']['writeofffee']
            except:
                spending = json.loads(r.text)['payTotal']
            total += float(spending)
            basic_info['monthly_consumption'].append(float(spending))
        basic_info['ave_monthly_consumption'] = round(total / len(basic_info['monthly_consumption']), 2)
        print('获得月消费')

        dump_json('basic_info.json', basic_info)

    def yzm_input(self, url, menuid):
        self.s.post(check_login)
        r = self.s.post(check_code_req.format('000100030001', unix_time))

        if json.loads(r.text)['verification'] is False:
            print('本次无需验证码')
            return

        send_code = 'http://iservice.10010.com/e3/static/query/sendRandomCode?_={}&accessURL={}&menuid={}'
        self.s.post(send_code.format(unix_time, url, menuid), data={'menuId': menuid})

        correct_input = False
        while correct_input is False:
            yzm = input('输入验证码：')

            if len(yzm) != 6:
                print('验证码错误，请重新输入')
                yzm = input('输入验证码：')

            submit_code = 'http://iservice.10010.com/e3/static/query/verificationSubmit?_={}&accessURL={}&menuid={}' \
                          '&inputcode={}&menuId={}'
            r = self.s.post(submit_code.format(unix_time, url, menuid, yzm, menuid))

            if json.loads(r.text)['flag'] == '00':
                print('验证码正确')
                correct_input = True
            else:
                print('验证码错误，请重新输入')
                continue

    def call_list(self):
        print('正在获取通话详单')
        menuid = '000100030001'
        call_detail_url = 'http://iservice.10010.com/e4/query/bill/call_dan-iframe.html?menuCode=000100030001'
        call_detail_list = 'http://iservice.10010.com/e3/static/query/callDetail?_={}&accessURL={}&menuid={}'

        self.yzm_input(call_detail_url, menuid)

        for month in self.last_day:
            first = month.strftime('%Y%m01')
            last = month.strftime('%Y%m%d')

            r = self.s.post(call_detail_list.format(unix_time, call_detail_url, menuid),
                            data={'pageNo': 1, 'pageSize': 100, 'beginDate': first, 'endDate': last})
            d = json.loads(r.text)

            if 'errorMessage' in d:
                if d['errorMessage']['respCode'] == '2114030170':
                    print('{}月无详单'.format(month.month))
                else:
                    print('网站错误，{}月详单获取失败'.format(month.month))
                continue
            else:
                r = self.s.get('http://iservice.10010.com/e3/ToExcel.jsp?type=sound')
                filename = r.headers['content-disposition'].encode('latin1').decode('utf8')
                keyword = 'filename='
                before_keyword, keyword, after_keyword = filename.partition(keyword)
                with open('excel/'+after_keyword, 'wb') as f:
                    f.write(r.content)
                print('获得{}月详单'.format(month.month))

    def msg_list(self):
        print('正在获取短信详单')
        menuid = '000100030002'
        msg_detail_url = 'http://iservice.10010.com/e4/query/calls/call_sms-iframe.html?menuCode=000100030002'
        msg_detail_list = 'http://iservice.10010.com/e3/static/query/sms?_={}&accessURL={}&menuid={}'

        self.yzm_input(msg_detail_url, menuid)

        for month in self.last_day:
            first = month.strftime('%Y%m01')
            last = month.strftime('%Y%m%d')

            r = self.s.post(msg_detail_list.format(unix_time, msg_detail_url, menuid),
                            data={'pageNo': 1, 'pageSize': 20, 'begindate': first, 'enddate': last})
            d = json.loads(r.text)

            if 'errorMessage' in d:
                if d['errorMessage']['respCode'] == '2114030170':
                    print('{}月无详单'.format(month.month))
                else:
                    print('网站错误，{}月详单获取失败'.format(month.month))
                continue
            else:
                r = self.s.get('http://iservice.10010.com/e3/ToExcel.jsp?type=sms3')
                filename = r.headers['content-disposition'].encode('latin1').decode('utf8')
                keyword = 'filename='
                before_keyword, keyword, after_keyword = filename.partition(keyword)
                with open('excel/'+after_keyword, 'wb') as f:
                    f.write(r.content)
                print('获得{}月详单'.format(month.month))

    def full_run(self):
        self.login()
        self.basic_info()
        self.call_list()
        self.msg_list()


if __name__ == '__main__':
    c = UnicomCrawlerRequests()
    c.full_run()

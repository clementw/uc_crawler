import os
import random
import re
import string
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from helper import dump_json

unix_time = str(round(time.time() * 1000.0))
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
     "Chrome/58.0.3029.110 Safari/537.36"
callback_str = 'jQuery1720' + ''.join(random.choices(string.digits, k=18)) + '_' + unix_time
accessURL = 'http://iservice.10010.com/e4/query/bill/call_dan-iframe.html?menuCode=000100030001'

check_captcha = 'https://uac.10010.com/portal/Service/CheckNeedVerify?'
login_url = 'https://uac.10010.com/portal/Service/MallLogin?redirectURL=http%3A%2F%2Fwww.10010.com&pwdType=01' \
            '&productType=01&redirectType=01&rememberMe=1'
hall_login = 'https://uac.10010.com/portal/hallLogin'
check_login = 'http://iservice.10010.com/e3/static/check/checklogin?_=' + unix_time
check_code_req = 'http://iservice.10010.com/e3/static/query/checkmapExtraParam?_=' + unix_time
send_code = 'http://iservice.10010.com/e3/static/query/sendRandomCode'
user_detail = 'http://iservice.10010.com/e3/static/query/searchPerInfoDetail/?_='
call_detail = 'http://iservice.10010.com/e4/query/bill/call_dan-iframe.html?menuCode=000100030001'
msg_detail = 'http://iservice.10010.com/e4/query/calls/call_sms-iframe.html?menuCode=000100030002'

province_dict = {'北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽',
                 '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃',
                 '青海', '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'}


class UnicomCrawler:
    def __init__(self):

        self.phone = input('输入手机号：')
        self.pwd = input('输入密码：')
        options = webdriver.ChromeOptions()
        prefs = {'download.default_directory': os.getcwd()}
        options.add_experimental_option('prefs', prefs)
        self.driver = webdriver.Chrome(chrome_options=options)

    def login(self):
        self.driver.get(hall_login)

        fill_phone = self.driver.find_element_by_name("userName")
        fill_phone.clear()
        fill_phone.send_keys(self.phone)

        fill_pwd = self.driver.find_element_by_id("userPwd")
        fill_pwd.clear()
        fill_pwd.send_keys(self.pwd)

        time.sleep(3)
        fill_pwd.send_keys(Keys.RETURN)
        time.sleep(3)

    def check_detail_exists(self):
        try:
            self.driver.find_element_by_xpath('//*[@id="queryError"]/div/p[1]')
        except NoSuchElementException:
            return True
        return False

    def yzm_input(self):
        self.driver.find_element_by_xpath('//*[@id="huoqu_buttons"]').click()
        time.sleep(5)
        yzm = input('输入验证码：')

        yzm_input = self.driver.find_element_by_xpath('//*[@id="input"]')
        yzm_input.clear()
        yzm_input.send_keys(yzm)
        self.driver.find_element_by_id('sign_in').click()
        time.sleep(15)

    def user_info(self):
        userinfo = {'operator': "CHINAUNICOM", 'operator_zh': "中国联通", 'id_card_check': 0, 'name_check': 0,
                    'if_call_emergency1': 0, 'if_call_emergency2': 0, 'monthly_consumption': [], 'phone_location': '',
                    'phone': self.phone, 'ave_monthly_consumption': ''}

        self.driver.get('http://iservice.10010.com/e4/query/others/service_belong.html?menuId=000400010003')
        number_input = self.driver.find_element_by_id('inputNnumber')
        number_input.send_keys(self.phone)
        number_input.send_keys(Keys.RETURN)
        time.sleep(2)
        userinfo['phone_location'] = self.driver.find_element_by_xpath('//*[@id="addr"]').text

        self.driver.get('http://iservice.10010.com/e4/query/basic/personal_xx.html')
        time.sleep(15)

        userinfo['id_card'] = self.driver.find_element_by_xpath(
            '//*[@id="userInfocontext"]/div[2]/div[1]/dl[3]/dd').text[7:18]

        userinfo['real_name'] = self.driver.find_element_by_xpath(
            '//*[@id="userInfocontext"]/div[2]/div[1]/dl[1]/dd').text

        userinfo['reg_date'] = self.driver.find_element_by_xpath(
            '//*[@id="numberContext"]/div[2]/div[2]/dl[1]/dd').text
        userinfo['reg_date'].replace('年', '-')
        userinfo['reg_date'].replace('月', '-')
        userinfo['reg_date'].replace('日', '-')

        self.driver.get('http://iservice.10010.com/e4/query/calls/account_balance.html?menuId=000100010013')
        time.sleep(20)
        userinfo['current_balance'] = float(self.driver.find_element_by_xpath(
            '//*[@id="userInfoContent"]/dl[2]/dd/i').text[:-2])

        self.driver.get('http://iservice.10010.com/e4/query/basic/history_list.html?menuId=000100020001')
        time.sleep(10)
        total_spending = 0

        i = 1
        while i <= 6:
            self.driver.find_element_by_xpath('//*[@id="score_list_ul"]/li[{}]'.format(i)).click()
            time.sleep(10)

            try:
                text = self.driver.find_element_by_xpath(
                    '//*[@id="historylistContext"]/table/tbody/tr/td[1]/table/tbody').text
            except:
                text = self.driver.find_element_by_xpath(
                    '//*[@id="historylistContext"]/table/tbody').text

            text = float(re.findall(r"[-+]?\d*\.\d+|\d+", text.rstrip())[-1])
            userinfo['monthly_consumption'].append(text)
            total_spending += text

            i += 1
            print(total_spending)
        userinfo['ave_monthly_consumption'] = round(total_spending / 6, 2)

        dump_json('basic_info.json', userinfo)

    def call_list(self):
        self.driver.get(call_detail)
        time.sleep(5)
        self.yzm_input()

        i = 1
        while i <= 6:
            self.driver.find_element_by_xpath('//*[@id="searchTime"]/ul/li[{}]'.format(i)).click()
            time.sleep(20)
            if self.check_detail_exists():
                self.driver.find_element_by_xpath('//*[@id="callDetailContent"]/div[5]/input[2]').click()
                time.sleep(10)
            else:
                print("无详单，继续爬取")
            i += 1

    def msg_list(self):
        self.driver.get(msg_detail)
        time.sleep(10)
        self.yzm_input()

        i = 1
        while i <= 6:
            self.driver.find_element_by_xpath('//*[@id="searchTime"]/ul/li[{}]'.format(i)).click()
            time.sleep(20)
            if self.check_detail_exists():
                self.driver.find_element_by_xpath('//*[@id="smsmmsResultTab"]/div[6]/input[2]').click()
                time.sleep(10)
            else:
                print("无详单，继续爬取")
            i += 1

        time.sleep(10)

    def end_crawl(self):
        self.driver.close()
        print('完成爬取')

    def full_run(self):
        self.login()
        # self.user_info()
        # self.call_list()
        self.msg_list()
        # self.end_crawl()

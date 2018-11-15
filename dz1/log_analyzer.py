#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import gzip
import os
import datetime
import time
import sys
import json
from string import Template
import logging
import ConfigParser
import argparse
from collections import namedtuple

# import gc
# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


config = {
    "REPORT_SIZE": 20,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "MAX_ERR": 30,
    "WORK_LOG": "./work_log"
}
config_file_global = "./log_analyzer.cfg"


# считыватель конфига
def config_reader(cfg_filepath, config_dict=config):
    # плохо итерироваться по словарю, который перебираем
    config_to_update = config_dict
    if os.path.isfile(cfg_filepath):
        config_file = config_file_global
        config = ConfigParser.RawConfigParser()
        config.read(cfg_filepath)
        for section_name in config.sections():
            for name, value in config.items(section_name):
                name = name.upper()
                if (name in config_dict):
                    config_to_update.update({name: value})
    else:
        logging.info("config file not found. I will use default config")
    # конвертим в инт значения размера отчета
    config_to_update.update({"REPORT_SIZE": int(config_to_update["REPORT_SIZE"])})
    config_to_update.update({"MAX_ERR": int(config_to_update["MAX_ERR"])})
    return config_to_update


# настройка лога
def worker_log(worklog_dir):
    if not os.path.exists(worklog_dir):
        os.makedirs(worklog_dir)
    worklog_file = os.path.join(worklog_dir,
                                'work_log-' + datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S") + '.log')
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', filename=worklog_file, filemode='w')
    logging.info("worker_log is set")


# декоратор время выполнения
def benchmark(original_func):
    def wrapper(*args, **kwargs):
        start = datetime.datetime.now()
        result = original_func(*args, **kwargs)
        end = datetime.datetime.now()
        logging.info('{0} is executed in {1}'.format(original_func.__name__, end - start))
        return result

    return wrapper


# функция проверки существования файла отчета
def check_report(report_dir, date_stamp):
    file_report_rend = os.path.join(report_dir, 'report-' + date_stamp.strftime(
        "%Y.%m.%d") + '.html')  # файл который рендерим, отчет
    if os.path.exists(file_report_rend):
        logging.info('File is exists  report ' + file_report_rend)
        return True
    else:
        logging.info('File not  exists  report '.format(sys._getframe().f_code.co_name, file_report_rend))
        return False


# функция открытия файла gzip или plain
def openfile(filename, file_ext):
    if (file_ext == '.gz'):
        return gzip.open(filename, 'rt')
    else:
        return open(filename, 'r')


# функция поиска самого свежего лога
def log_finder(log_dir):
    dict_files = {}
    extract_err = 0
    file_tuple = namedtuple('file_tuple', ['filename', 'file_date', 'file_ext'])
    for filename in os.listdir(log_dir):
        match = re.match(r'^nginx-access-ui\.log-(?P<date>\d{8})(?P<file_ext>\.gz)?$', filename)
        if not match:
            continue
        file_ext = match.groupdict()['file_ext']
        extract_date = datetime.datetime.strptime(match.groupdict()['date'], '%Y%m%d')
        year = extract_date.year
        month = '{:02d}'.format(extract_date.month)
        day = '{:02d}'.format(extract_date.day)
        str_date = str(year) + '.' + str(month) + '.' + str(day)
        dict_files.update({filename: {'filedate': extract_date.date(), 'ext': file_ext}})
    for key, value in sorted(dict_files.items(), key=lambda x: x[1]['filedate'], reverse=True)[:1]:
        last_file = file_tuple(key, value['filedate'], value['ext'])
    return last_file


# функция сравнения двух  максимальногозначения времени
def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    if (abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)):
        return b
    else:
        return a


# функция поиска медианы
def median(lst):
    n = len(lst)
    if n < 1:
        return None
    if n % 2 == 1:
        return sorted(lst)[n // 2]
    else:
        return sum(sorted(lst)[n // 2 - 1:n // 2 + 1]) / 2.0


# на вход подавать имя файла
@benchmark
def reader(log_dir, file_log, ext, max_err):
    logging.info("reader start")
    error_counter = 0  # счетчик ошибок
    unique_urlcnt = 0  # счетчик уникальных урлов
    timetotal_url = 0  # счетчик уникальных урлов
    time_urls = {}  # словарь содержит url и время
    file_log = os.path.join(log_dir, file_log)
    if not os.path.isfile(file_log):
        return
    else:
        with openfile(file_log, ext) as inputfile:
            lines_cnt = 0  # ограничемся пока 1000 строк
            for line in inputfile:
                finded = line.split(' ')
                urls = finded[7].strip()
                time = float(line[-6:])
                # словарь статистики состоит из:time_url-время урла , url_count количества
                time_list = []  # список времени для урла,по нему будем считать медиану
                try:
                    if urls in time_urls:
                        time_list = time_urls[urls]['time_mass']
                        time_list.append(time)
                        time_urls.update({urls: {"time_sum": time_urls[urls]['time_sum'] + time,
                                                 "time_mass": time_list, "cnt": time_urls[urls]["cnt"] + 1}})
                    else:
                        time_list.append(time)
                        time_urls.update({urls: {"time_sum": time, "time_mass": time_list, "cnt": 1}})
                        unique_urlcnt += 1

                except Exception as exc:
                    error_counter += 1
                    logging.exception(exc)
                lines_cnt += 1
                timetotal_url += time
    return time_urls, error_counter, unique_urlcnt, lines_cnt, timetotal_url


# функция для подсчета процентов на вход словарь с урлами и временем, на выходе словарь урл, время, процент процентами
@benchmark
def percent_url_counter(dict, uniq_url, time_sum, err):
    dict_percent = dict
    logging.info("percent_url_counter start")
    for k, v in dict.iteritems():
        dict_percent[k]["count_perc"] = 100 * float(dict[k]["cnt"]) / float(uniq_url)
        dict_percent[k]["time_perc"] = 100 * dict[k]["time_sum"] / float(time_sum)
        dict_percent[k]["time_avg"] = dict[k]["time_sum"] / dict[k]["cnt"]
        list_to_max = dict_percent[k]["time_mass"]
        dict_percent[k]["time_max"] = max(list_to_max)
        dict_percent[k]["time_med"] = median(list_to_max)

    return dict


# функция возвращает топ записей из массива
def top_values(dict_stat, top_count):
    logging.info("top_values start")
    cntgot = 0  # количество занчений которое отдали, top_count которое требуется отдать
    list_to_render = []
    for key, value in sorted(dict_stat.items(), key=lambda x: x[1]['time_sum'], reverse=True):
        list_to_render.append({"count": value['cnt'],
                               "time_avg": value['time_avg'],
                               "time_max": value['time_max'],
                               "time_sum": value['time_sum'],
                               "url": key,
                               "time_med": value['time_med'],
                               "time_perc": value['time_perc'],
                               "count_perc": value['count_perc']
                               })
        cntgot += 1
        if (cntgot == top_count):
            logging.info("top_values: получено запрошенное количество значений . Топчик")
            jsonarr = json.dumps(list_to_render)
            break
        else:
            jsonarr = json.dumps(list_to_render[cntgot - 1])
    return jsonarr


# функция рендеринга html файла
def json_templater(json_array, report_dir, date_stamp):
    file_report = os.path.join(report_dir, 'report.html')  # файл шаблона
    file_report_rend = os.path.join(report_dir, 'report-' + date_stamp.strftime(
        "%Y.%m.%d") + '.html')  # файл который рендерим, отчет
    logging.info(file_report)
    if os.path.isfile(file_report):
        with open(file_report, 'r') as report_template:
            render_data = report_template.read()
            t = Template(render_data)
            data_export = t.safe_substitute(table_json=json_array)
        # здесь нужно писать во временный файл, потом делать мув
        with open(file_report_rend, 'w') as output_file:
            output_file.write(data_export)
    else:
        loggin.error(file_report + ' file not found')


def main(config_dictionary):
    report_sz = config_dictionary["REPORT_SIZE"]
    rep_dir = config_dictionary["REPORT_DIR"]
    wl = config_dictionary["WORK_LOG"]
    logfolder = config_dictionary["LOG_DIR"]
    max_err = config_dictionary["MAX_ERR"]
    worker_log(wl)# инициализация лога
    file_info = log_finder(logfolder)
    if (check_report(rep_dir, file_info.file_date) == False):
        timeurls, errcnt, uniquecnt, total_cnt, total_time = reader(logfolder, file_info.filename, file_info.file_ext,
                                                                    max_err)
        # доля ошибок парсинга
        parse_err = errcnt * 100 / total_cnt
        if (parse_err <= max_err):
            final_dict = percent_url_counter(timeurls, uniquecnt, total_time, errcnt)
            json_mass = top_values(final_dict, report_sz)
            json_templater(json_mass, rep_dir, file_info.file_date)
        else:
            logging.exception('Log parse errors is ' + str(max_err) + '%. Exit program!!!!!')
            sys.exit()
    else:
        logging.info(" REPORT уже существует. Повторный запуск не требуется")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help="Config file path", default=config_file_global)
    args = parser.parse_args()
    if args.config:
        dict_config = config_reader(args.config)
    else:
        dict_config = config_reader(config_file_global)
    try:
        main(dict_config)
    except Exception as exc:
        logging.exception(exc)

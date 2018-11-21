#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ConfigParser
import argparse
import datetime
import gzip
import json
import logging
import os
import re
import shutil
import copy
from collections import namedtuple
from string import Template

# import gc
# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


DEFAULT_CONFIG = {
    "REPORT_SIZE": 20,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "MAX_ERR": 30,
    "WORK_LOG": "./work_log"
}
CONFIG_FILE_GLOBAL = "./log_analyzer.cfg"


# считыватель конфига
def config_reader(cfg_filepath, config_dict):
    config_tuple = namedtuple('config_tuple', ['report_sz', 'report_dir', 'log_dir', 'max_err', 'work_log'])
    # плохо итерироваться по словарю, который перебираем
    config_to_update = copy.deepcopy(config_dict)
    if os.path.isfile(cfg_filepath):
        config = ConfigParser.RawConfigParser()
        config.read(cfg_filepath)
        for section_name in config.sections():
            for name, value in config.items(section_name):
                name = name.upper()
                if name in config_dict:
                    config_to_update.update({name: value})
    else:
        logging.info("config file not found. I will use default config")
    # конвертим в инт значения размера отчета
    config_to_update.update({"REPORT_SIZE": int(config_to_update["REPORT_SIZE"])})
    config_to_update.update({"MAX_ERR": int(config_to_update["MAX_ERR"])})
    new_config = config_tuple(config_to_update["REPORT_SIZE"], config_to_update["REPORT_DIR"],
                              config_to_update["LOG_DIR"],
                              config_to_update["MAX_ERR"], config_to_update["WORK_LOG"])

    return new_config


# настройка лога
def worker_log(worklog_dir):
    if not os.path.exists(worklog_dir):
        os.makedirs(worklog_dir)
    worklog_file = os.path.join(worklog_dir,
                                'work_log-{0}.{1}'.format(datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S"), 'log'))
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


def openfile(filename):
    if filename.endswith('.gz'):
        return gzip.open(filename, 'rt')
    else:
        return open(filename, 'r')


# функция поиска самого свежего лога
def log_finder(log_dir):
    dict_files = {}
    max_key = ""
    file_tuple = namedtuple('file_tuple', ['filename', 'file_date', 'file_ext'])
    for filename in enumerate(os.listdir(log_dir)):
        match = re.match(r'^nginx-access-ui\.log-(?P<date>\d{8})(?P<file_ext>\.gz)?$', filename)
        if not match:
            continue

        try:
            extract_date = datetime.datetime.strptime(match.groupdict()['date'], '%Y%m%d')
        except Exception as exc:
            logging.exception(exc)
        dict_files.update({filename: {'filedate': extract_date.date()}})
    max_key = max(dict_files.keys(), key=(lambda k: dict_files[k]))
    last_file = file_tuple(max_key, dict_files[max_key]["filedate"])
    return last_file


# функция поиска медианы
def median(lst):
    n = len(lst)
    if n < 1:
        return None
    if n % 2 == 1:
        return sorted(lst)[n // 2]
    else:
        return sum(sorted(lst)[n // 2 - 1:n // 2 + 1]) / 2.0


@benchmark
def nginx_log_reader(log_dir, file_log, max_errors):
    logging.info("reader start")
    error_counter = 0  # счетчик ошибок
    unique_urlcnt = 0  # счетчик уникальных урлов
    timetotal_url = 0  # счетчик уникальных урлов
    time_urls = {}  # словарь содержит url и время
    file_log = os.path.join(log_dir, file_log)
    if not os.path.isfile(file_log):
        return
    with openfile(file_log) as inputfile:
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
        # доля ошибок парсинга
        if lines_cnt > 0:
            err_percent_cnt = 100 * float(error_counter) / float(lines_cnt)
            max_err_percent = 100 * float(max_errors) / float(lines_cnt)
        else:
            err_percent_cnt = float(1)
            max_err_percent = float(1)
    return time_urls, unique_urlcnt, timetotal_url, err_percent_cnt, max_err_percent


# функция для подсчета процентов на вход словарь с урлами и временем, на выходе словарь урл, время, процент процентами
@benchmark
def percent_url_counter(dict_in, uniq_url, time_sum):
    dict_percent = dict_in
    logging.info("percent_url_counter start")
    for k, v in dict_in.iteritems():
        dict_percent[k]["count_perc"] = 100 * float(dict_in[k]["cnt"]) / float(uniq_url)
        dict_percent[k]["time_perc"] = 100 * dict_in[k]["time_sum"] / float(time_sum)
        dict_percent[k]["time_avg"] = dict_in[k]["time_sum"] / dict_in[k]["cnt"]
        list_to_max = dict_percent[k]["time_mass"]
        dict_percent[k]["time_max"] = max(list_to_max)
        dict_percent[k]["time_med"] = median(list_to_max)

    return dict_percent


# функция возвращает топ записей из массива
def top_values(dict_stat, top_count):
    logging.info("top_values start")
    cntgot = 0  # количество занчений которое отдали, top_count которое требуется отдать
    list_to_render = []
    if top_count == len(dict_stat):
        top_count = len(dict_stat)
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
        if cntgot == top_count:
            logging.info("top_values: received requested number of values.")
            break
    return list_to_render


# функция рендеринга html файла
def json_templater(input_list, report_dir, date_stamp):
    json_array = json.dumps(input_list)
    file_report = os.path.join(report_dir, 'report.html')  # файл шаблона
    file_report_rend = os.path.join(report_dir, 'report-{0}.{1}'.format(date_stamp.strftime("%Y.%m.%d"), 'html'))
    file_report_rend_tmp = os.path.join(report_dir,
                                        'report-{0}_{1}.{2}'.format(date_stamp.strftime("%Y.%m.%d"), 'tmp', 'html'))
    logging.info(file_report)
    if os.path.isfile(file_report):
        with open(file_report, 'r') as report_template:
            render_data = report_template.read()
            t = Template(render_data)
            data_export = t.safe_substitute(table_json=json_array)
        with open(file_report_rend_tmp, 'w') as output_file:
            output_file.write(data_export)
        # переписываем в отчет
        shutil.move(file_report_rend_tmp, file_report_rend)
    else:
        logging.error(file_report + ' file not found')


def main(config_tuple):
    worker_log(config_tuple.work_log)  # инициализация лога
    file_info = log_finder(config_tuple.log_dir)
    if os.path.exists(os.path.join(config_tuple.report_dir,
                                   'report-{0}.{1}'.format(file_info.file_date.strftime("%Y.%m.%d"), 'html'))):
        logging.info(" REPORT exists. No restart required")
    else:
        timeurls, uniquecnt, total_time, err_perc_cnt, max_erros_perc = nginx_log_reader(
            config_tuple.log_dir,
            file_info.filename,
            config_tuple.max_err)
        if err_perc_cnt < max_erros_perc:
            final_dict = percent_url_counter(timeurls, uniquecnt, total_time)
            list_values = top_values(final_dict, config_tuple.report_sz)
            json_templater(list_values, config_tuple.report_dir, file_info.file_date)
        else:
            logging.exception('Maximum error threshold reached {0}% . Exit program!!!!!'.format(str(max_erros_perc)))


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help="Config file path", default=CONFIG_FILE_GLOBAL)
    args = parser.parse_args()
    conf_tup = config_reader(args.config or CONFIG_FILE_GLOBAL, DEFAULT_CONFIG)
    try:
        main(conf_tup)
    except Exception as exc:
        logging.exception(exc)

# Project Title

Ngnix Log parser 

## Getting Started
Лог парсер предназначен для парсинга логов
написан как дз по логам

### Prerequisites

python2.7


Give examples
run:
./log_parser.py  для запуска с настройками по умолчанию
./log_parser.py  --config <имя файла> для запуска с настройками пользователя
Формать конфига
[ConfiLog1]
REPORT_SIZE: 125  #топ записей из лога с самыми большими time_sum гкд
REPORT_DIR: ./reports # куда складывать отчеты
LOG_DIR: ./log  # где смотреть логи
MAX_ERR: 1000   #максимальное количество ошибок парсинга логов
WORK_LOG:./work_log # директория с трейсами скрипта

## Running the tests
пока не написал тестов

## Versioning


## Authors

* **Sergei Larichkin** - - https://github.com/enzo1920/

## License



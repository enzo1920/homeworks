# Project Title

Crawler to PDF

## Getting Started
Это модификация ДЗ-11
Краулер скачивает интересующие страницы с сайта news.ycombinator.com, сохраняет их в pdf и отправляет на почту.
Используется утилита wkhtmltopdf для конвертации вэбстраниц в pdf.
### Prerequisites
Тесты проводились на ubuntu 18.04
python3.7
wkhtmltopdf
xvfb

Give examples
Перед запуском необходимо запустить виртуальный дисплей(для работы wkhtmltopdf):
```
export DISPLAY=":1" 
./xvfb_run.sh 
```
run:
```
./crawler2_pdf.py  для запуска с настройками по умолчанию
./crawler2_pdf.py  --config <имя файла> для запуска с настройками пользователя
```
Формать конфига
```
[ConfiLog1]
server:ctest.ctest.com:25,
mail_from":ctest@test.com,
mail_pass":testpass,
mail_destination":tomail@ctest.com,
timeout_smtp:20
```
Файлы в pdf сохраняются в storedir
Далее отправляются по поче.
## Running the tests
пока не написал тестов

## Versioning


## Authors

* **Sergei Larichkin** - - https://github.com/enzo1920/

## License



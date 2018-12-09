# HTTP server#
Асинхронный веб сервер частично реализующий протокол HTTP, prefork .
## Getting Started##

### Prerequisites###

python2.7


Give examples
run:
./dummy_http.py  для запуска с настройками по умолчанию
Flags:
-r  root directory, default  ./www`
-l, log directory, default./log`
-p, port  default   8080`
-w, process worker, default 6`


## Running the tests##
## ApacheBench##


Server Software:        dummy_http`
Server Hostname:        188.227.18.141`
Server Port:            8080`

Document Path:          /`
Document Length:        119 bytes`

Concurrency Level:      100`
Time taken for tests:   12.934 seconds`
Complete requests:      50000`
Failed requests:        0`
Total transferred:      13000000 bytes`
HTML transferred:       5950000 bytes`
Requests per second:    3865.85 [#/sec] (mean)`
Time per request:       25.868 [ms] (mean)`
Time per request:       0.259 [ms] (mean, across all concurrent requests)`
Transfer rate:          981.56 [Kbytes/sec] received`

Connection Times (ms)`
              min  mean[+/-sd] median   max`
Connect:        0    7 154.9      0    7012`
Processing:     2   17  19.9     13    1605`
Waiting:        1   16  19.9     13    1605`
Total:          3   24 163.2     13    8615`

Percentage of the requests served within a certain time (ms)`
  50%     13`
  66%     16`
  75%     19`
  80%     22`
  90%     27`
  95%     30`
  98%     34`
  99%     40`
 100%   8615 (longest request)`

## httptest.py##

directory index file exists ... ok`
document root escaping forbidden ... ok`
Send bad http headers ... ok`
file located in nested folders ... ok`
absent file returns 404 ... ok`
urlencoded filename ... ok`
file with two dots in name ... ok`
query string after filename ... ok`
filename with spaces ... ok`
Content-Type for .css ... ok`
Content-Type for .gif ... ok`
Content-Type for .html ... ok`
Content-Type for .jpeg ... ok`
Content-Type for .jpg ... ok
Content-Type for .js ... ok`
Content-Type for .png ... ok`
Content-Type for .swf ... ok`
head method support ... ok`
directory index file absent ... ok`
large file downloaded correctly ... ok`
post method forbidden ... ok`
Server header exists ... ok`

----------------------------------------------------------------------`
Ran 22 tests in 0.242s`
OK






* **Sergei Larichkin** - - https://github.com/enzo1920/



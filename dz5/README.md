# uWSGI Daemon 
Daemon gets your IP, checks your location and gets weather forecast


### Requirements
- CentOS 7
- Python 2.7
- python configparser library
- systemd
- nginx

### How to install:
- Clone repo from github:
```
git clone https://github.com/enzo1920/homeworks.git
cd dz5

ip2w-0.0.1-1.noarch.rpm
```

### Start daemon
 
systemctl start ip2w


### Query 
```
curl http://your_ip:8080/87.250.250.242
{"city": "Moscow", "conditions": "mist", "temp": -15.20999999999998}
```

### Stop daemon
```
systemctl stop ip2w
```



## Running the tests
### ip2w_tests.py
```
Send malformed IP ... ok
Send empty IP (server must take it from headers) ... ok
Send good IP ... ok
Send URL with large level of nesting ... ok
Send IP from reserved range ... ok

----------------------------------------------------------------------
Ran 5 tests in 8.351s

OK
```


* **Sergei Larichkin** - - https://github.com/enzo1920/



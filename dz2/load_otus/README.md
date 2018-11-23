# Project Title

Patch for opcodes

## Getting Started


### Prerequisites

python2.7.6
сделно по статье https://blog.quarkslab.com/building-an-obfuscated-python-interpreter-we-need-more-opcodes.html
LOAD_OTUS
Для сборки патча:
исходники python 2.7.6 
git clone https://github.com/enzo1920/python2.7.6_for_optests.git

далее переключаемся(создаем) на ветку git checkout -b load_otus_fix
далее , то что лежит в папке src р распихиваем по папкам питона: 
Include/opcode.h, 
Lib/opcode.py, 
Python/peephole.c, 
Python/ceval.c
далее
./configure
и
make
 запускаем ./python 
 
 далее по статье:
 https://www.devroom.io/2009/10/26/how-to-create-and-apply-a-patch-with-git/
  
## Versioning


## Authors

* **Sergei Larichkin** - - https://github.com/enzo1920/

## License



# DTSPRJ1
Invoice / UPI parser

## Install Dependencies
install the required modules

for best and safe use create and use a venv:
```bash
python -m venv venv

.venv\Scripts\activate
```
To install the dependencies:
```bash
pip install requirements.txt
```
## How to use:
Run program and enter the file path you need parsed :
![App Screenshot](readme-assets/program_use_screenshot-1.png)

[NOTE:] use of " " throws an error . Do not use " " in file path.

example: 

with quotes: throws an error
["c:\users\documents\filename.png"]- this wont work

without quotes:
[c:\users\documents\filename.png]- works

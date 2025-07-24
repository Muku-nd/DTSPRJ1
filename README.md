# DTSPRJ1
Invoice / UPI parser

## STEP1: Install OCR AND PDF SOFTWARES
  ✅ Install Tesseract

   **Windows:**
   1. Download from [UB Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki)
   2. Install and add the install folder (e.g., `C:\Program Files\Tesseract-OCR`) to your **System PATH**
   3. Test after installation in cmd:
      
   ```bash
      tesseract --version
   ```
      
   **Mac:**
   
  ```bash
       brew install tesseract
  ```

   **Linux:**

  ```bash
       sudo apt update
       sudo apt install tesseract-ocr
  ```
    
   ✅ Install  Poppler

   **Windows:**
   1. Download from [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases/)
   2. Install and add the install folder (e.g., `C:\Program Files\poppler`) to your **System PATH**
   3. Test after installation in cmd:
      
  ```bash
      pdftoppm -v
  ```
      
   **Mac:**
   
  ```bash
       brew install poppler
  ```

   **Linux:**

  ```bash
       sudo apt update
       sudo apt install poppler-utils
  ```
   
## STEP2: Install Parser DTSPRJ-1:

to install create a new folder in Documents/Downloads:
![new folder screenshot](readme-assets/new-folder.png)

next type cmd in the folder path to open the folder in terminal:
![cmd_screenshot](readme-assets/cmd_in_folder.png)

next clone repo to use program:
![cmd_clone](clone_repo.png)
 Clone repo inside folder (open folder in terminal)
   ```bash
      git clone https://github.com/Muku-nd/DTSPRJ1.git
   ```
next navigate to project folder:
![cmd_navigate](readme-assets/cmd_navigate.png)

next go into repo folder:
   ```bash
      cd DTSPRJ1
   ```

## STEP3: Install Dependencies
install the required modules

for best and safe use create and use a venv:

```bash
python -m venv venv

.venv\Scripts\activate
```
should look like:
![venv](readme-assets/venv_create.png)

To install the dependencies:

```bash
pip install -r requirements.txt
```
should look like:
![pip](pip_install.png)


## STEP3: How to use:

   navigate to parser file:
   ```bash
      cd Parser
   ```
   should look like :
   ![Parser](Parser_folder.png)
   THIS IS A CLI TOOL SO RUN IT ON TERMINAL: 
   
   run python file:
   ```bash
      python parser2.py
   ```
   should look like:
   ![python run](python_run.png)
   **BEFORE YOU RUN THE CODE MAKE SURE YOUR RUNNING IT IN THE CORRECT DIRECTORY . that is inside your DTSPRJ1 folder.**


   Run program: enter the file path you need parsed :
   ![App Screenshot](terminal_enter_file.png)
   
**[NOTE:] use of " " throws an error . Do not use " " while entering file path.**


example: 

with quotes: throws an error
**["c:\users\documents\filename.png"]**- this wont work

without quotes:works
**[c:\users\documents\filename.png]**- works

FROM python:3.9.6-buster

WORKDIR /root/Horoscope

# INSTALL DEPENDENCIES FOR DOCTR
RUN apt-get update \
 && apt-get install -y libgl1-mesa-dev libsm6 libxext6 libxrender-dev \
    tesseract-ocr tesseract-ocr-fra

# INSTALL PIPENV
RUN pip3 install pipenv

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pipenv install --dev --system --deploy
#--dev — Install both develop and default packages from Pipfile.
#--system — Use the system pip command rather than the one from your virtualenv.
#--deploy — Make sure the packages are properly locked in Pipfile.lock, and abort if the lock file is out-of-date.

# FIX THIS
# Unable to add extras in Pipfile for DocTR, pipenv raises an error
RUN pip3 install python-doctr['torch']

CMD python3 -u bot.py

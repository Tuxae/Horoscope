FROM python:3.6.9

WORKDIR /root/Horoscope

RUN pip3 install --upgrade pip

ADD requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-fra

CMD python3 -u horoscope_bot.py

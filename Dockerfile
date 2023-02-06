FROM python:3.9.6

WORKDIR /

COPY requirements.txt /

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "main.py", "--sym1=MATICUSDT" ]
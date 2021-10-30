build:
	docker build -t horoscope .
run:
	docker run -d -v $PWD:/root/Horoscope --name horoscope horoscope
buidl_lock:
	docker build -t lock -f lock.Dockerfile .
lock:
	docker run -v $PWD:/usr/src/app --rm lock pipenv lock

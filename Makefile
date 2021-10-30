build:
	docker build -t horoscope .
run:
	docker run -d -v $(PWD):/root/Horoscope --name horoscope horoscope
build_lock:
	docker build -t lock -f Dockerfile.lock .
lock:
	docker run -v $(PWD):/root/Horoscope --rm lock pipenv lock

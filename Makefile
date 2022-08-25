build:
	docker-compose build
up:
	docker-compose -p horoscope up -d
down:
	docker-compose -p horoscope down -t 0

run:
	docker run -d -v $(PWD):/root/Horoscope --name horoscope horoscope
build_lock:
	docker build -t lock -f Dockerfile.lock .
lock:
	docker run -v $(PWD):/root/Horoscope --rm lock pipenv lock

run_selenium:
	docker run --rm -d -p 4444:4444 --name selenium-horoscope --shm-size=2g selenium/standalone-chrome

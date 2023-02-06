.PHONY: docker-up
docker-up: # rebuild Docker image
	docker build -t statbot:test .
	docker run -d --name statbot statbot:test

.PHONY: docker-down
docker-down: # stop running container
	docker stop statbot
	docker rm statbot

.PHONY: docker-stop
docker-stop:
	docker stop statbot




IP=`ifconfig eth0 | sed -n 's/.*inet addr:\([^ ]*\) .*/\1/p'`
FRONTEND_HOST_PORT=8000
FRONTEND_GUEST_PORT=8000
WORKER_PORT=5678
WORKER_ADDR=tcp://${IP}:${WORKER_PORT}

build:
	sudo docker build -t frontend cloudasr/frontend/
	sudo docker build -t worker cloudasr/worker/

run:
	sudo docker run --name frontend -p ${FRONTEND_HOST_PORT}:${FRONTEND_GUEST_PORT} -e WORKER_ADDR=${WORKER_ADDR} -d frontend
	sudo docker run --name worker -p ${WORKER_PORT}:${WORKER_PORT} -e MY_ADDR=tcp://0.0.0.0:${WORKER_PORT} -d worker

stop:
	sudo docker stop frontend worker
	sudo docker rm frontend worker
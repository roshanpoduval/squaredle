FROM python:3.8

RUN pip install DAWG

CMD python3 test_dawg.py

# docker build . -t dawg_image -f dawg.dockerfile; docker run --name dawg_container -v $(pwd):$(pwd) -w $(pwd) -it dawg_image ; nohup docker container rm dawg_container
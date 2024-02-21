FROM debian:bookworm

#RUN dpkg --add-architecture i386
RUN apt-get update
RUN apt-get -y upgrade

RUN apt-get -y install curl libgomp1
    #wine wine64 libwine fonts-wine wine32 libwine:i386
WORKDIR /app
RUN curl -L https://github.com/vdemichev/DiaNN/releases/download/1.8.1/diann_1.8.1.tar.gz -o diann_1.8.1.tar.gz
RUN tar zxvf diann_1.8.1.tar.gz

ENTRYPOINT ["./diann-1.8.1"]
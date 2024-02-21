FROM debian:bookworm
ENV DEBIAN_FRONTEND noninteractive

RUN dpkg --add-architecture i386

RUN apt-get update
RUN apt-get -y upgrade

RUN apt-get -y install curl libgomp1 gnupg wget xvfb
    #wine wine64 libwine fonts-wine wine32 libwine:i386

WORKDIR /app
RUN curl -L https://github.com/vdemichev/DiaNN/releases/download/1.8.1/diann_1.8.1.tar.gz -o diann_1.8.1.tar.gz
RUN tar zxvf diann_1.8.1.tar.gz
RUN mkdir -pm755 /etc/apt/keyrings
RUN wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
RUN wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources

RUN apt-get update
RUN apt-get -y install --install-recommends winehq-devel
RUN useradd -d /home/diann -m -s /bin/bash diann && echo diann:diann | chpasswd

RUN apt-get install -y cabextract
RUN wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
RUN chmod +x winetricks
RUN cp winetricks /usr/local/bin
RUN wget -P /mono https://dl.winehq.org/wine/wine-mono/9.0.0/wine-mono-9.0.0-x86.msi




USER diann

ENV WINEPREFIX=/home/diann/.wine WINEARCH=win64
#RUN winecfg
#RUN wineboot -u && winetricks -q dotnet452
#RUN wineboot -u && msiexec /i /mono/wine-mono-9.0.0-x86.msi
#RUN rm -f /tmp/.X*-lock && xvfb-run -e /dev/stdout sh -c "wineboot && winetricks --optout --force -q vcrun2008 && winetricks --optout --force -q vcrun2010 && winetricks --optout --force -q vcrun2015  && wineserver -w"
#RUN winecfg
#USER root
COPY diann /home/diann/.wine
COPY ["MRC-Astral", "/home/diann/.wine/drive_c/data"]

#COPY ["wine/drive_c/DIA-NN", "/home/diann/.wine/drive_c/DIA-NN"]
#COPY ["wine/drive_c/Program Files (x86)/Thermo", "/home/diann/.wine/drive_c/Program Files (x86)/Thermo"]
#COPY ["wine/drive_c/Program Files/Thermo", "/home/diann/.wine/drive_c/Program Files/Thermo"]
#COPY ["wine/drive_c/Program Files/Common Files", "/home/diann/.wine/drive_c/Program Files/Common Files"]
USER root
RUN chown -R diann:diann /home/diann/.wine
USER diann
#ENTRYPOINT ["wine", "/home/diann/.wine/drive_c/DIA-NN/1.8.1/DiaNN.exe"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
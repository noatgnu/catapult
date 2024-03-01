FROM chambm/pwiz-skyline-i-agree-to-the-vendor-licenses

#RUN winecfg
#RUN wineboot -u && winetricks -q dotnet452
#RUN wineboot -u && msiexec /i /mono/wine-mono-9.0.0-x86.msi
#RUN rm -f /tmp/.X*-lock && xvfb-run -e /dev/stdout sh -c "wineboot && winetricks --optout --force -q vcrun2008 && winetricks --optout --force -q vcrun2010 && winetricks --optout --force -q vcrun2015  && wineserver -w"
#RUN winecfg
#USER root

COPY ["MRC-Astral", "/wineprefix64/drive_c/data"]
COPY ["wine/drive_c/DIA-NN", "/wineprefix64/drive_c/DIA-NN"]
#COPY ["wine/drive_c/Program Files (x86)/Thermo", "/home/diann/.wine/drive_c/Program Files (x86)/Thermo"]
#COPY ["wine/drive_c/Program Files/Thermo", "/home/diann/.wine/drive_c/Program Files/Thermo"]
#COPY ["wine/drive_c/Program Files/Common Files", "/home/diann/.wine/drive_c/Program Files/Common Files"]
#ENTRYPOINT ["wine", "/home/diann/.wine/drive_c/DIA-NN/1.8.1/DiaNN.exe"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
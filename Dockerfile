FROM ubuntu

RUN apt update -y
RUN apt install -y python3-pip git cmake python3.10-venv libtins-dev sqlite coreutils libboost-all-dev tcpdump libcairo2-dev

WORKDIR /src
COPY . .

RUN ./build.sh

# https://stackoverflow.com/questions/65410481/filenotfounderror-errno-2-no-such-file-or-directory-bliblibc-a/65513989#65513989
RUN cd /usr/lib/x86_64-linux-gnu/ && ln -s -f libc.a liblibc.a
CMD tail -f /dev/null

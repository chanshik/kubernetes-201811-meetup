# 실습 환경 구축

## Programs

### USB

`USB/programs` 디렉토리에 Virtualbox, Vagrant 파일이 저장되어 있습니다.



### Web

강의장에서 알려준 IP 로 접속하면 `/programs` 디렉토리에서 원하는 운영체제에 맞는 파일을 받을 수 있습니다.



## APT proxy

강의장에서 알려준 IP 와 Port (3241) 를 이용해 APT proxy 설정을 추가하여 apt 를 이용해 프로그램을 설치할 때 캐시된 파일을 이용할 수 있습니다.

### VM 에 APT proxy 설정 추가

`/etc/apt/apt.conf.d/00proxy` 파일을 추가하여 apt 에서 이용할 Proxy 설정을 넣어줍니다.

```bash
# cat <<END > /etc/apt/apt.conf.d/00proxy
Acquire::http { Proxy "http://[IP]:3142"; };
END
```



## Vagrant Box

### USB

`USB/ubuntu-VAGRANTSLASH-bionic64` 디렉토리를 `~/.vagrant.d/boxes` 안으로 복사합니다.



## Web

강의장에서 알려준 IP 로 접속해 `/box/ubuntu-VAGRANTSLASH-bionic64.tgz` 파일을 받아서 압축을 풀고, `~/.vagrant.d/boxes` 안으로 복사합니다.



## Docker Images

Vagrant 를 이용해 VM 을 실행하면, `/vagrant` 디렉토리를 통해 `kubernetes-201811-meetup` 디렉토리에 접근할 수 있습니다. Docker 이미지를 받은 이후에 작업은 VM 내부에서 진행합니다.



## USB

`USB/docker-images` 안에 있는 파일을 `kubernetes-201811-meetup/docker` 디렉토리에 모두 복사합니다.



## Web

강의장에서 알려준 IP 를 `download-images.py` 프로그램 인자로 넘겨주면 필요한 도커 이미지를 모두 다운 받습니다.

```bash
/vagrant/docker$ python3 download_images.py [IP]
```



## Load docker Images

 USB 혹은 Web 을 통해 이미지를 받은 이후에 VM 에서 아래 프로그램을 실행하여 Docker 이미지를 등록합니다.

```bash
/vagrant/docker$ python3 load_docker_images.py
```


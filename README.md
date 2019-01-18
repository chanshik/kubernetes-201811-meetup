# Kubernetes Hands-on with VM

VM 환경 (Virtualbox) 에서 Kubernetes 클러스터를 직접 구축하는 실습을 진행합니다. 

* Kubernetes 를 바로 설치해볼 수 있도록 Vagrant 를 이용해 VM 을 실행하고 클러스터 구성
* Helm, Ceph, Rook, Metallb 등을 활용해서 어플리케이션 배포



## Used packages in this hands-on

* Kubernetes (http://kubernetes.io)
* Docker (https://www.docker.com/)
* Helm (https://helm.sh)
* Rook (https://rook.io)
* Ceph (https://ceph.com)
* Metallb (https://metallb.universe.tf)



# Setup Environments

* Host OS: Ubuntu 16.04
* Guest OS: Ubuntu 16.04 (ubuntu/xenial64) / 18.04 (ubuntu/bionic64)
* Automation Tool: Vagrant



## Install Virtualbox

사용하는 운영체제에 맞는 패키지를 받아 설치합니다.

* https://www.virtualbox.org/wiki/Downloads

```bash
sudo apt install virtualbox
```



## Install Vagrant 

VM 을 생성하면서 기본적인 초기화를 진행할 때 사용할 Vagrant 프로그램을 설치합니다.

* https://www.vagrantup.com/downloads.html

```bash
sudo dpkg -i vagrant_2.2.1_x86_64.deb
```



## Downloads Vagrant box image

Vagrant 를 이용해 VM 을 생성할 때 사용할 Box 파일을 미리 받아 디스크에 저장해둡니다.

Ubuntu 16.04 혹은 18.04 이미지를 이용합니다.

```bash
vagrant box add ubuntu/bionic64
```



## Downloads worksheet

github 저장소에 실습을 진행하면서 사용할 파일을 디렉토리별로 구분하여 저장해두었습니다.

```bash
git clone https://github.com/chanshik/kubernetes-201811-meetup.git
cd kubernetes-201811-meetup
kubernetes-201811-meetup$ 
```



## VM Networks

VM 에 할당한 IP 와 역할은 다음과 같습니다.

| Node  | IP         | Role   |
| ----- | ---------- | ------ |
| k8s-1 | 10.254.1.2 | Master |
| k8s-2 | 10.254.1.3 | Worker |
| k8s-3 | 10.254.1.4 | Wokrer |



## Start VMs

미리 작성해둔 **Vagrantfile** 을 이용해 VM 3대를 시작합니다. 사용하는 장비 사양에 맞도록 CPU, 메모리, 추가 디스크 공간을 지정합니다.

실습에 필요한 환경을 구축하기 위해 세 대의 VM 이 실행되며, 각 VM 은 시스템 디스크 외에 두 개의 디스크를 더 가지고 있습니다. **/dev/sdc** 디스크는 배포하는 어플리케이션이 노드에 종속적인 디스크를 사용할 경우에 할당되는 공간이며, **/dev/sdd** 디스크는 **Ceph** 클러스터에서 활용하게 됩니다.

```ruby
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/bionic64"
  config.vm.box_check_update = false
  node_subnet = "10.254.1"

  (1..3).each do |i|
    config.vm.define "k8s-#{i}" do |node|
      node.vm.hostname = "k8s-#{i}"
      node.vm.network "private_network", ip: "#{node_subnet}.#{i + 1}"

      attached_disk_a = "disk-k8s-#{i}-a.vdi"
      attached_disk_b = "disk-k8s-#{i}-b.vdi"

      node.vm.provider "virtualbox" do |vb|
        vb.name = "k8s-#{i}"
        vb.gui = false

        vb.cpus = 2
        vb.memory = "4096"

        unless File.exists?(attached_disk_a)
          vb.customize [
            'createhd', '--filename', attached_disk_a,
            '--variant', 'Fixed',
            '--size', 10 * 1024]
        end

        unless File.exists?(attached_disk_b)
          vb.customize [
            'createhd', '--filename', attached_disk_b,
            '--variant', 'Fixed',
            '--size', 10 * 1024]
        end

        vb.customize [
          'storageattach', :id, '--storagectl', 'SCSI',
          '--port', 2, '--device', 0, '--type', 'hdd',
          '--medium', attached_disk_a]

        vb.customize [
          'storageattach', :id, '--storagectl', 'SCSI',
          '--port', 3, '--device', 0, '--type', 'hdd',
          '--medium', attached_disk_b]
      end

      node.vm.provision "bootstrap", type: "shell", inline: <<-SHELL
        sudo curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
        sudo bash -c 'cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF'
        sudo apt update
        sudo apt install -y docker.io kubelet kubeadm kubectl ntp nfs-kernel-server
        sudo usermod -aG docker vagrant

        sudo sed -i '/k8s/d' /etc/hosts
        sudo echo "#{node_subnet}.#{i + 1} k8s-#{i}" | sudo tee -a /etc/hosts

        sudo mkfs.ext4 /dev/sdc
        sudo mkdir /media/data
      SHELL

      node.vm.provision "shell", run: "always",
        inline: "sudo mount /dev/sdc /media/data"
    end
  end
end
```

앞에서 작성한 **Vagrantfile** 을 이용해 VM 을 생성합니다.

```bash
vagrant up
```

VM 생성이 모두 끝난 다음에 ssh 를 실행하여 원하는 노드에 접속합니다.

```bash
vagrant ssh k8s-1
```



## Slow network environment

네트워크 속도가 느린 곳에서는 VM 을 생성하면서 패키지를 설치하는 방식보다, VM 을 모두 시작한 이후에 터미널로 접속해서 필요한 작업을 진행합니다.

```bash
vagrant up --no-provision
```

VM 을 실행한 이후에 각 VM 에 접속해서 초기 작업을 진행합니다.

```bash
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

sudo bash -c 'cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF'

sudo apt update
sudo apt install -y docker.io kubelet kubeadm kubectl ntp nfs-kernel-server
sudo usermod -aG docker vagrant

sudo sed -i '/k8s/d' /etc/hosts
sudo echo "10.254.1.2 k8s-1" | sudo tee -a /etc/hosts
```

초기화 단계를 진행할 때  `sudo echo "10.254.1.2 k8s-1" | sudo tee -a /etc/hosts` 명령은 각 VM 에 접속해서  노드 이름과 IP 를 개별로 지정해서 실행합니다.



## Format data disk

VM 에 추가한 2개 디스크 중에 하나를 **ext4** 형식으로 포맷해서 준비해둡니다. Vagrant 를 이용해 VM 을 생성할 때, 기본적인 작업이 이루어지도록 추가해두었습니다. 만약에 **Provision** 단계를 건너뛰었다면, 각 노드에 접속하여 디스크 초기화 작업을 진행해 **Persistent Volume** 으로 사용할 디스크를 준비해두어야 합니다.

```bash
sudo mkfs.ext4 /dev/sdc

mke2fs 1.44.1 (24-Mar-2018)
Found a dos partition table in /dev/sdc
Proceed anyway? (y,N) y
Creating filesystem with 2621440 4k blocks and 655360 inodes
Filesystem UUID: dfac8c39-ef7c-43dc-8594-b81467306723
Superblock backups stored on blocks: 
	32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632

Allocating group tables: done                            
Writing inode tables: done                            
Creating journal (16384 blocks): done
Writing superblocks and filesystem accounting information: done 

```

```bash
sudo mkdir /media/data
sudo mount /dev/sdc /media/data
```

```bash
df -h

Filesystem      Size  Used Avail Use% Mounted on
udev            2.0G     0  2.0G   0% /dev
tmpfs           395M  1.1M  394M   1% /run
/dev/sda1       9.7G  3.1G  6.7G  32% /
tmpfs           2.0G     0  2.0G   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
tmpfs           2.0G     0  2.0G   0% /sys/fs/cgroup
vagrant         267G   84G  183G  32% /vagrant
tmpfs           395M     0  395M   0% /run/user/1000
/dev/sdc        9.8G   37M  9.3G   1% /media/data
```



# Setup Kubernetes Cluster

## Select pod network add-on

Kubernetes 에서 사용할 CNI (Container Network Interface) 선택하고 **kubeadm** 을 이용해 초기화 할 때 같이 지정합니다. 실습에서는 **Calico** CNI 를 사용합니다.

* kubeadm 은 CNI 기반 네트워크만 지원
* Calico CIDR: 192.168.0.0/16
* https://kubernetes.io/docs/concepts/cluster-administration/addons/



## Initialize master node

Master node 에서 **kubeadm init** 명령을 실행하여 클러스터 초기화 작업을 시작합니다.

```bash
sudo swapoff -a
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=10.254.1.2

[init] using Kubernetes version: v1.12.2
[preflight] running pre-flight checks
	[WARNING Service-Docker]: docker service is not enabled, please run 'systemctl enable docker.service'
[preflight/images] Pulling images required for setting up a Kubernetes cluster
[preflight/images] This might take a minute or two, depending on the speed of your internet connection
[preflight/images] You can also perform this action in beforehand using 'kubeadm config images pull'
[kubelet] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
[kubelet] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[preflight] Activating the kubelet service
...
[bootstraptoken] using token: s9qd0j.beetbemlhmmx1etd
[bootstraptoken] configured RBAC rules to allow Node Bootstrap tokens to post CSRs in order for nodes to get long term certificate credentials
[bootstraptoken] configured RBAC rules to allow the csrapprover controller automatically approve CSRs from a Node Bootstrap Token
[bootstraptoken] configured RBAC rules to allow certificate rotation for all node client certificates in the cluster
[bootstraptoken] creating the "cluster-info" ConfigMap in the "kube-public" namespace
[addons] Applied essential addon: CoreDNS
[addons] Applied essential addon: kube-proxy

Your Kubernetes master has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

You should now deploy a pod network to the cluster.
Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/

You can now join any number of machines by running the following on each node
as root:

  kubeadm join 10.254.1.2:6443 --token dzjclo.a8d0kjwcc64r7kvs --discovery-token-ca-cert-hash sha256:ce7c94f7863dbc1ad8d32028cb5388e4ea47a12959317d035b722e2a4fb3e5f3
```



## Add nodes

Master node 초기화 이후에는 추가하려는 노드에서 **kubeadm join** 명령을 실행합니다.

**@k8s-2**

```bash
sudo swapoff -a
sudo kubeadm join 10.254.1.2:6443 --token s9qd0j.beetbemlhmmx1etd --discovery-token-ca-cert-hash sha256:573bf08c800f2c9736d9b1b8a66421777dcd9e8991a2b9e0d7612c248bcdcdc5
```

**@k8s-3**

```bash
sudo swapoff -a
sudo kubeadm join 10.254.1.2:6443 --token s9qd0j.beetbemlhmmx1etd --discovery-token-ca-cert-hash sha256:573bf08c800f2c9736d9b1b8a66421777dcd9e8991a2b9e0d7612c248bcdcdc5
```



## Show kubernetes nodes

위 과정을 거쳐 생성한 Kubernetes 에 접근하려면 /etc/kubernetes/admin.conf 파일이 필요합니다. 홈 디렉토리에 복사하고 소유자를 변경한 이후에 **KUBECONFIG** 환경변수에 위치를 지정합니다.

```bash
sudo cp /etc/kubernetes/admin.conf ./k8s-admin.conf
sudo chown vagrant:vagrant k8s-admin.conf 
export KUBECONFIG=/home/vagrant/k8s-admin.conf
echo "export KUBECONFIG=/home/vagrant/k8s-admin.conf" >> .bashrc
kubectl get nodes

NAME    STATUS     ROLES    AGE     VERSION
k8s-1   NotReady   master   8m48s   v1.12.2
k8s-2   NotReady   <none>   2m31s   v1.12.2
k8s-3   NotReady   <none>   2m28s   v1.12.2
```



## Install CNI

**kubectl get nodes** 명령 결과를 보면 **STATUS** 가 현재 **NotReady** 입니다. 초기화 단계에서 선택한 CNI 를 설치해야 실제로 사용 가능한 상태가 됩니다.

**Calico** CNI 를 사용하기 위해 **kubectl** 명령어를 이용해 설치합니다. 

```bash
kubectl apply -f https://docs.projectcalico.org/v3.3/getting-started/kubernetes/installation/hosted/rbac-kdd.yaml

clusterrole.rbac.authorization.k8s.io/calico-node created
clusterrolebinding.rbac.authorization.k8s.io/calico-node created
```

```bash
kubectl apply -f https://docs.projectcalico.org/v3.3/getting-started/kubernetes/installation/hosted/kubernetes-datastore/calico-networking/1.7/calico.yaml

configmap/calico-config created
service/calico-typha created
deployment.apps/calico-typha created
poddisruptionbudget.policy/calico-typha created
daemonset.extensions/calico-node created
serviceaccount/calico-node created
customresourcedefinition.apiextensions.k8s.io/felixconfigurations.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/bgppeers.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/bgpconfigurations.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/ippools.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/hostendpoints.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/clusterinformations.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/globalnetworkpolicies.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/globalnetworksets.crd.projectcalico.org created
customresourcedefinition.apiextensions.k8s.io/networkpolicies.crd.projectcalico.org created
```

```bash
kubectl get nodes
NAME    STATUS   ROLES    AGE   VERSION
k8s-1   Ready    master   25m   v1.12.2
k8s-2   Ready    <none>   19m   v1.12.2
k8s-3   Ready    <none>   19m   v1.12.2
```



## Master isolation

Kubernetes 기본 설정은 Master 역할을 하는 노드에 다른 컨테이너를 배포하지 않도록 되어있습니다. 실습을 진행할 때는 Master 노드도 사용하기 위해 설정을 변경합니다.

```bash
kubectl taint nodes --all node-role.kubernetes.io/master- 

node/k8s-1 untainted
taint "node-role.kubernetes.io/master:" not found
taint "node-role.kubernetes.io/master:" not found
```



## Install dashboard

Kubernetes 를 편하게 사용하기 위해 Dashboard 를 설치합니다.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/master/aio/deploy/recommended/kubernetes-dashboard.yaml

secret/kubernetes-dashboard-certs created
serviceaccount/kubernetes-dashboard created
role.rbac.authorization.k8s.io/kubernetes-dashboard-minimal created
rolebinding.rbac.authorization.k8s.io/kubernetes-dashboard-minimal created
deployment.apps/kubernetes-dashboard created
service/kubernetes-dashboard created
```

Dashboard 에서 사용할 계정을 생성하는데, 여기에서는 관리자 권한을 준 **admin-user** 를 생성하여 접속하는데 이용합니다.

**kubernetes/dashboard-service-account.yaml**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kube-system
```

**kubernetes/dashboard-clusterrolebinding.yaml**

```yaml
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kube-system
```

위 두 파일을 이용하여 Dashboard 에 접속할 때 사용할 계정을 생성합니다.

```bash
kubectl create -f kubernetes/dashboard-service-account.yaml 
serviceaccount/admin-user created
kubectl create -f kubernetes/dashboard-clusterrolebinding.yaml 
clusterrolebinding.rbac.authorization.k8s.io/admin-user created
```

설치한 Dashboard 상태를 확인합니다.

```bash
kubectl get svc -n kube-system

NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)         AGE
calico-typha           ClusterIP   10.100.9.93     <none>        5473/TCP        2m53s
kube-dns               ClusterIP   10.96.0.10      <none>        53/UDP,53/TCP   24m
kubernetes-dashboard   ClusterIP   10.105.107.14   <none>        443/TCP         119s
```

외부에서 접속하기 위해 **Dashboard Service Type** 을 **NodePort** 로 변경합니다.

```bash
kubectl edit svc -n kube-system kubernetes-dashboard
```

vi 에디터 화면에서 **nodePort** 를 추가하고 **type** 에 **NodePort** 를 지정합니다.

```yaml
spec:
  clusterIP: 10.105.107.14
  ports:
  - port: 443
    protocol: TCP
    targetPort: 8443
    nodePort: 30000
  selector:
    k8s-app: kubernetes-dashboard
  sessionAffinity: None
  type: NodePort
```

```bash
$ kubectl get svc -n kube-system kubernetes-dashboard

NAME                   TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)         AGE
kubernetes-dashboard   NodePort   10.105.107.14   <none>        443:30000/TCP   3m54s
```

웹 브라우져를 통해 Dashboard 에 접속합니다.

![dashboard-intro](./assets/dashboard-intro.png)



## Get dashboard bearer token

Dashboard 에 접속하기 위해 관리자 Token 을 가져옵니다.

```bash
kubectl get secret -n kube-system                                                     

NAME                                             TYPE                                  DATA   AGE
admin-user-token-9m6zn                           kubernetes.io/service-account-token   3      115s
attachdetach-controller-token-htnpk              kubernetes.io/service-account-token   3      5m38s
bootstrap-signer-token-6ztxm                     kubernetes.io/service-account-token   3      5m52s
bootstrap-token-11h5df                           bootstrap.kubernetes.io/token         7      5m52s
calico-node-token-2kxw5                          kubernetes.io/service-account-token   3      2m43s
certificate-controller-token-6lvgq               kubernetes.io/service-account-token   3      5m52s
...
```

```bash
kubectl describe secret admin-user-token-9m6zn -n kube-system                         

Name:         admin-user-token-9m6zn
Namespace:    kube-system
Labels:       <none>
Annotations:  kubernetes.io/service-account.name: admin-user
              kubernetes.io/service-account.uid: 407a5a06-ed68-11e8-a94d-02c44c503abe

Type:  kubernetes.io/service-account-token

Data
====
namespace:  11 bytes
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuLTltNnpuIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI0MDdhNWEwNi1lZDY4LTExZTgtYTk0ZC0wMmM0NGM1MDNhYmUiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06YWRtaW4tdXNlciJ9.dhPeoOsMCwmvwNFWFPE6Gn16afd0CpY22uOzNliEgYyALoZndU-j2r62gm3W697UzfatWg5Ezj7m52mq3wKkhr1tHZeEUXHBjmRulOh_sbtJJKBOACGDl9yhWSbhb8F5NMfWhqBnpFwKws9uL3mapiN5Pks8z4yky-pZf3SMpFNtvo_FtoynNbnxo_kalOhvMeqNrpZrJZBGCCCFR9Z9uDu3kaDqsVrfNrMZE0Yx6Rk8TIma9_gibSr57va8XSLFa35P31UwFTHiafVFyOSyvp9ZHkVw2Me-V_SYYQmfjZjjBXr8QZSeEjp8mTJMD5R_NInkl37DtVCG6uf8xUuzjw
ca.crt:     1025 bytes
```

마지막 token: 밑에 있는 문자열을 이용해 Dashboard 에 접속할 수 있습니다.



![dashboard-overview](./assets/dashboard-overview.png)



# Isolate resources

## Use label

Kubernetes 에서 어플리케이션을 실행할 때 특정 노드에서만 실행되도록 할 수 있습니다. Managed Kubernetes 에서는 이렇게 사용할 이유가 없겠지만, 내부에서 클러스터를 구축해 사용한다면 유용하게 사용할 수 있습니다.

노드에 부여되어 있는 Label 을 확인해봅니다.

```bash
kubectl get nodes --show-labels

NAME      STATUS   ROLES    AGE   VERSION   LABELS
k8s-1     Ready    master   80m   v1.12.2   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/os=linux,kubernetes.io/hostname=k8s-1,node-role.kubernetes.io/master=
k8s-2     Ready    <none>   80m   v1.12.2   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/os=linux,kubernetes.io/hostname=k8s-2
k8s-3     Ready    <none>   79m   v1.12.2   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/os=linux,kubernetes.io/hostname=k8s-3
```

**beta.kubernetes.io/arch**, **beta.kubernetes.io/os**, **kubernetes.io/hostname** Label 들은 클러스터에 참여하고 있는 노드들에 부여한 기본적인 속성입니다. 특정한 노드에만 어플리케이션이 동작하도록 설정하려면, **kubernetes.io/hostname** Label 을 이용합니다. 

앞으로는 일반적인 목적을 가진 어플리케이션을 실행하는데 사용할 Label 로 **app** 를 사용하겠습니다.

```bash
kubectl label nodes k8s-1 k8s-2 k8s-3 app=yes

node/k8s-1 labeled
node/k8s-2 labeled
node/k8s-3 labeled
```



### Deploy nginx with label

nginx 어플리케이션을 Kubernetes 에서 배포하면서 실행할 노드를 label 을 이용해 지정해보겠습니다.

**nginx/nginx-deploy.yaml**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    k8s-app: nginx
  name: nginx
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      k8s-app: nginx
  template:
    metadata:
      labels:
        k8s-app: nginx
      name: nginx
    spec:
      containers:
      - image: nginx
        name: nginx
      nodeSelector:
        app: "yes"
```

**nginx/nginx-svc.yaml**

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    k8s-app: nginx
  name: nginx-svc
  namespace: default
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
    nodePort: 31000
  selector:
    k8s-app: nginx
  type: NodePort
```

Deploy 와 Service 생성 파일을 이용해 어플리케이션을 배포합니다.

```bash
kubectl create -f nginx/nginx-deploy.yaml

deployment.apps/nginx created
```

```bash
kubectl get deploy

NAME    DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
nginx   1         1         1            0           12s
```

```bash
kubectl create -f nginx/nginx-svc.yaml

service/nginx-svc created
```

```bash
kubectl get svc

NAME         TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
kubernetes   ClusterIP   10.96.0.1        <none>        443/TCP        117m
nginx-svc    NodePort    10.109.129.149   <none>        80:31000/TCP   3s
```

Service 에서 **NodePort** 로 지정한 31000 번으로 접속하여 nginx 서비스가 배포된 것을 확인할 수 있습니다.

![nginx-web](./assets/nginx-web.png)



## Use namespace

Kubernetes 에서 생성한 모든 객체는 기본적으로 **default** namespace 에 속하게 됩니다. 사용자 접근 제어 혹은 자원 관리를 namespace 단위로 하는 것이 권장합니다. 여기에서는 어플리케이션 단위로 namespace 를 생성해 사용해보도록 하겠습니다.

```bash
kubectl create namespace redis

namespace/redis created
```

```bash
kubectl get namespace
NAME          STATUS   AGE
default       Active   98m
kube-public   Active   98m
kube-system   Active   98m
redis         Active   7s
```



# Setup Helm

Helm 은 Kubernetes Package Manager 로서 어플리케이션을 구성하는 여러 컴포넌트를 패키지로 묶어서 쉽게 배포하고 관리할 수 있게 도움을 줍니다.

## Install helm

```bash
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get | bash

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  7236  100  7236    0     0   7452      0 --:--:-- --:--:-- --:--:--  7444
Downloading https://kubernetes-helm.storage.googleapis.com/helm-v2.11.0-linux-amd64.tar.gz
Preparing to install helm and tiller into /usr/local/bin
helm installed into /usr/local/bin/helm
tiller installed into /usr/local/bin/tiller
Run 'helm init' to configure helm.
```



## Create service account

helm 에서 사용할 Service Account 를 생성합니다.

**helm/rbac-config.yaml**

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tiller
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tiller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: tiller
    namespace: kube-system
```

```bash
kubectl apply -f helm/rbac-config.yaml 

serviceaccount/tiller created
clusterrolebinding.rbac.authorization.k8s.io/tiller created
```



## Update repository

설치한 helm 을 초기화하고 **stable** 패키지 리스트를 가져옵니다.

```bash
helm init --service-account tiller --node-selectors "app"="yes"

Creating /home/vagrant/.helm 
Creating /home/vagrant/.helm/repository 
Creating /home/vagrant/.helm/repository/cache 
Creating /home/vagrant/.helm/repository/local 
Creating /home/vagrant/.helm/plugins 
Creating /home/vagrant/.helm/starters 
Creating /home/vagrant/.helm/cache/archive 
Creating /home/vagrant/.helm/repository/repositories.yaml 
Adding stable repo with URL: https://kubernetes-charts.storage.googleapis.com 
Adding local repo with URL: http://127.0.0.1:8879/charts 
$HELM_HOME has been configured at /home/vagrant/.helm.

Tiller (the Helm server-side component) has been installed into your Kubernetes Cluster.

Please note: by default, Tiller is deployed with an insecure 'allow unauthenticated users' policy.
To prevent this, run `helm init` with the --tiller-tls-verify flag.
For more information on securing your installation see: https://docs.helm.sh/using_helm/#securing-your-helm-installation
Happy Helming!
```

```bash
helm repo update

Hang tight while we grab the latest from your chart repositories...
...Skip local chart repository
...Successfully got an update from the "stable" chart repository
Update Complete. ⎈ Happy Helming!⎈ 
```



# Setup Metallb

## NodePort, LoadBalancer

Kubernetes 에서 외부에서 접속할 수 있도록 서비스를 열어두는 방법에는 두 가지가 있습니다. NodePort 는 30000 ~ 32767 (기본 범위) 포트를 내부 서비스와 연결하여 외부에서 접속을 가능하도록 허용해줍니다. LoadBalancer 는 서비스에 접근할 수 있는 특정 IP 를 할당하여 외부에서 할당된 IP 를 통해 내부 서비스에 접근할 수 있습니다. Cloud Platform 에서 Kubernetes  클러스터를 생성하거나 Managed Kubernetes 를 이용할 경우에는 각 Cloud Platform 에서 제공하는 LoadBalancer 를 활용할 수 있습니다.



## Metallb

Kubernetes 를 Bare metal 클러스터로 구축한 경우에는 Metallb 를 이용해 LoadBalancer 로 사용할 수 있습니다.

Metallb 에서는 Layer 2 mode 와 BGP mode 를 통해 서비스 IP 를 부여하는 방법을 제공하는데, 여기에서는 Layer 2 mode 를 이용하여 외부 IP 를 부여하도록 하겠습니다.



## Install Metallb

```bash
kubectl apply -f https://raw.githubusercontent.com/google/metallb/v0.7.3/manifests/metallb.yaml

namespace/metallb-system created
serviceaccount/controller created
serviceaccount/speaker created
clusterrole.rbac.authorization.k8s.io/metallb-system:controller created
clusterrole.rbac.authorization.k8s.io/metallb-system:speaker created
role.rbac.authorization.k8s.io/config-watcher created
clusterrolebinding.rbac.authorization.k8s.io/metallb-system:controller created
clusterrolebinding.rbac.authorization.k8s.io/metallb-system:speaker created
rolebinding.rbac.authorization.k8s.io/config-watcher created
daemonset.apps/speaker created
deployment.apps/controller created
```



## Configure LoadBalancer IP range

LoadBalancer 로 사용할 IP 대역을 설정 파일 안에 기술하여 지정할 수 있습니다. 여기에서는 10.254.1.150 ~ 10.254.1.250 을 외부에서 접속할 때 사용할 IP 대역으로 할당하였습니다.

**metallb/layer2-config.yaml**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: metallb-system
  name: config
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - 10.254.1.150-10.254.1.250
```

```bash
kubectl create -f metallb/layer2-config.yaml

configmap/config created
```



## Access Dashboard using LoadBalancer

앞에서는 Dashboard 를 NodePort 로 외부에 개방했는데, LoadBalancer 를 이용해 미리 지정한  외부에서 접속 가능하도록 변경해봅니다.

```bash
kubectl edit svc kubernetes-dashboard -n kube-system
```

```yaml
...
spec:
  clusterIP: 10.101.69.172
  externalTrafficPolicy: Cluster
  ports:
  - nodePort: 30000
    port: 443
    protocol: TCP
    targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard
  sessionAffinity: None
  type: LoadBalancer
...
```

IP 가 제대로 할당되었는지 확인합니다.

```bash
kubectl get svc -n kube-system

NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP    PORT(S)         AGE
kubernetes-dashboard   LoadBalancer   10.101.69.172    10.254.1.150   443:30000/TCP   14h
```

![dashboard-lb](./assets/dashboard-lb.png)



# Setup Redis with Helm

## Create storage directory

Redis 에서 사용할 디렉토리를 배포할 노드에 미리 생성해두고 권한을 조정합니다.

**@k8s-1**

```bash
sudo mkdir /media/data/redis
sudo chmod 777 /media/data/redis
```

**@k8s-2**

```bash
sudo mkdir /media/data/redis
sudo chmod 777 /media/data/redis
```

**@k8s-3**

```bash
sudo mkdir /media/data/redis
sudo chmod 777 /media/data/redis
```



## Deploy redis-ha

Redis 를 위해 Namespace 를 생성하고 **helm** 을 이용해 서비스를 배포합니다. 실행할 Redis 컨테이너는 **app=yes** label 을 가지고 있는 노드에 배포되며, **PersistentVolume** 으로 5Gi 공간을 요청합니다. 

```bash
kubectl create namespace redis

namespace/redis created
```

```bash
helm install --set "nodeSelector.app"="yes","persistentVolume.size"="5Gi" -n redis-k8s --namespace redis stable/redis-ha

NAME:   redis-k8s
LAST DEPLOYED: Sun Nov 18 03:11:14 2018
NAMESPACE: redis
STATUS: DEPLOYED

RESOURCES:
==> v1/Pod(related)
NAME                         READY  STATUS   RESTARTS  AGE
redis-k8s-redis-ha-server-0  0/2    Pending  0         0s

==> v1/ConfigMap

NAME                          AGE
redis-k8s-redis-ha-configmap  0s

==> v1/Service
redis-k8s-redis-ha  0s

==> v1/StatefulSet
redis-k8s-redis-ha-server  0s


NOTES:
Redis cluster can be accessed via port 6379 on the following DNS name from within your cluster:
redis-k8s-redis-ha.redis.svc.cluster.local

To connect to your Redis server:
1. Run a Redis pod that you can use as a client:

   kubectl exec -it redis-k8s-redis-ha-server-0 sh -n redis

2. Connect using the Redis CLI:

  redis-cli -h redis-k8s-redis-ha.redis.svc.cluster.local
```

서비스를 배포하는 데 필요한 PersistentVolume 을 생성하지 않았기 때문에, **Pending** 상태에 머물러 있습니다.

```bash
kubectl get pods -n redis

NAME                          READY   STATUS    RESTARTS   AGE
redis-k8s-redis-ha-server-0   0/2     Pending   0          6m59s
```

노드에 데이터를 저장할 공간을 미리 초기화를 진행했던 별도 디스크로 지정합니다.

**redis/redis-storage-pv.yaml**

```yaml
kind: PersistentVolume
apiVersion: v1
metadata:
  name: redis-pv-1
  labels:
    type: local
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/media/data/redis"
```

redis-ha 에서 기본적으로 실행시키는 컨테이너는 3 입니다. 그러므로 세 개의 PersistentVolume 을 생성합니다.

```bash
kubectl create -f redis/redis-storage-pv.yaml

persistentvolume/redis-pv-1 created
persistentvolume/redis-pv-2 created
persistentvolume/redis-pv-3 created
```

PersistentVolume 을 생성하면 PersistentVolumeClaim 과 연결하여 Pod 을 생성하기 시작합니다.

```bash
kubectl get pods -n redis

NAME                          READY   STATUS    RESTARTS   AGE
redis-k8s-redis-ha-server-0   2/2     Running   0          12m
redis-k8s-redis-ha-server-1   2/2     Running   0          10m
redis-k8s-redis-ha-server-2   2/2     Running   0          10m
```

Pod 배포가 마무리되면 외부에서 Redis 에 접속할 수 있도록 설정합니다.

**redis/redis-svc.yaml**

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app: redis-ha
    chart: redis-ha-3.0.1
    heritage: Tiller
    release: redis-k8s
  name: redis-k8s-redis-ha-svc
  namespace: redis
spec:
  ports:
  - name: server
    port: 6379
    protocol: TCP
    targetPort: redis
  - name: sentinel
    port: 26379
    protocol: TCP
    targetPort: sentinel
  selector:
    app: redis-ha
    release: redis-k8s
  type: LoadBalancer
```

Redis 에 LoadBalancer 를 설정한 후에 외부에서 접속하여 값을 기록하고 읽어봅니다.

```bash
kubectl create -f redis/redis-svc.yaml

service/redis-k8s-redis-ha-svc created
```

```bash
kubectl get svc -n redis
NAME                     TYPE           CLUSTER-IP      EXTERNAL-IP    PORT(S)                          AGE
redis-k8s-redis-ha       ClusterIP      None            <none>         6379/TCP,26379/TCP               11h
redis-k8s-redis-ha-svc   LoadBalancer   10.110.125.91   10.254.1.151   6379:32696/TCP,26379:30121/TCP   10s
```

```bash
redis-cli -h 10.254.1.151

10.254.1.151:6379> SET cluster.name "kubernetes"
OK
10.254.1.151:6379> GET cluster.name
"kubernetes"
```



# Setup Ceph with Rook

## Ceph and Rook

Kubernetes 위에서 동작하는 어플리케이션이 저장 공간을 필요로 할 경우에는 Persistent Volume 을 생성하여 연결해주어야 합니다. 여기에서는 **Ceph** 분산 파일 시스템을 이용하여 실행된 노드에 관계없이 원하는 저장 공간을 생성하고 연결하는 데 활용합니다.

Ceph 클러스터를 직접 구축하고 설정하는 것은 쉽지 않은 일이지만, **Rook** 을 이용해 상대적으로 쉽고 편리하게 구축할 수 있습니다. 아래는 Rook 프로젝트 홈페이지에서 가져온 Rook 소개글입니다.

> Rook is an open source **cloud-native storage orchestrator**,
> providing the platform, framework, and support for a diverse set of 
> storage solutions to natively integrate with cloud-native environments.

Rook 을 이용해 클러스터를 생성할 때 사용하는 설정 파일은 https://github.com/rook/rook/tree/release-0.8/cluster/examples/kubernetes/ceph 경로에 있는 것을 사용합니다.



## Initialize Ceph Cluster

VM 노드 3대가 가지고 있는 디스크 중에 아무런 작업을 하지 않은 디스크(**/dev/sdd**)를 Ceph 에 할당하여 클러스터를 구성합니다. Ceph 에서 사용하는 파일 시스템 중에 **BlueStore** 는 직접 파티션을 생성하고 관리하기 때문에, 노드에 장착되어 있는 빈 디스크를 직접 지정합니다. 미리 작성해둔 Vagrantfile 에서는 **/dev/sdd** 장치에 아무런 파티션 작업도 하지 않은 디스크를 연결해두었습니다.

**Rook Operator** 를 통해 Ceph 클러스터를 생성할 때 필요한 몇 가지 설정을 rook/operator.yaml 파일에 기록합니다.

**rook/operator.yaml**

```yaml
    ...
    spec:
      serviceAccountName: rook-ceph-system
      containers:
      - name: rook-ceph-operator
        image: rook/ceph:v0.8.3
        ...
        - name: ROOK_ALLOW_MULTIPLE_FILESYSTEMS
          value: "true"
        ...
        - name: ROOK_HOSTPATH_REQUIRES_PRIVILEGED
          value: "true"
        ...
```

**rook/ceph** 컨테이너 버전을 현재 Stable 상태인 **v0.8.3** 으로 지정합니다. 그리고 Shared File System 을 두 개 이상 만들어서 사용하려면 **ROOK_ALLOW_MULTIPLE_FILESYSTEMS** 옵션을 "true" 로 지정합니다. 

**BlueStore** 를 사용하려면 컨테이너에서 직접 파일 시스템을 생성할 수 있어야 하기 때문에 **ROOK_HOSTPATH_REQUIRES_PRIVILEGED** 옵션에 **"true"** 를 지정합니다.

**operator.yaml** 파일을 수정하고 **Rook operator** 를 배포합니다.

```bash
kubectl create -f rook/operator.yaml

namespace/rook-ceph-system created
customresourcedefinition.apiextensions.k8s.io/clusters.ceph.rook.io created
customresourcedefinition.apiextensions.k8s.io/filesystems.ceph.rook.io created
customresourcedefinition.apiextensions.k8s.io/objectstores.ceph.rook.io created
customresourcedefinition.apiextensions.k8s.io/pools.ceph.rook.io created
customresourcedefinition.apiextensions.k8s.io/volumes.rook.io created
clusterrole.rbac.authorization.k8s.io/rook-ceph-cluster-mgmt created
role.rbac.authorization.k8s.io/rook-ceph-system created
clusterrole.rbac.authorization.k8s.io/rook-ceph-global created
serviceaccount/rook-ceph-system created
rolebinding.rbac.authorization.k8s.io/rook-ceph-system created
clusterrolebinding.rbac.authorization.k8s.io/rook-ceph-global created
deployment.apps/rook-ceph-operator created
```

**cluster.yaml** 파일에 Ceph 에서 사용할 디스크 장치명을 나열합니다.

**rook/cluster.yaml**

```yaml
  ...
  storage:
    useAllNodes: false
    useAllDevices: false
    deviceFilter:
    location:
    config:
      storeType: bluestore
      databaseSizeMB: "1024"
      journalSizeMB: "1024"
    nodes:
      - name: "k8s-1"
        devices:
        - name: "sdd"
      - name: "k8s-2"
        devices:
        - name: "sdd"
      - name: "k8s-3"
        devices:
        - name: "sdd"
```

각 노드에서 사용할 디스크 장치명을 추가한 후 Ceph 클러스터를 생성합니다.

```bash
kubectl create -f rook/cluster.yaml

namespace/rook-ceph created
serviceaccount/rook-ceph-cluster created
role.rbac.authorization.k8s.io/rook-ceph-cluster created
rolebinding.rbac.authorization.k8s.io/rook-ceph-cluster-mgmt created
rolebinding.rbac.authorization.k8s.io/rook-ceph-cluster created
cluster.ceph.rook.io/rook-ceph created
```

만약에 Rook 으로 Ceph 클러스터를 한번 생성한 이후에 삭제하고 다시 생성하려면 **/var/lib/rook/osd-\***, **/var/lib/rook/mon-\*** 디렉토리를 모두 지운 이후에 위 명령을 다시 실행합니다.

디스크 파티션 작업을 마무리하고 모두 완료되면 **rook-ceph** namespace 에서 배포된 Ceph 구성요소를 확인할 수 있습니다.

```bash
kubectl get deploy -n rook-ceph

NAME              DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
rook-ceph-mgr-a   1         1         1            1           112s
rook-ceph-mon-a   1         1         1            1           2m31s
rook-ceph-mon-b   1         1         1            1           2m15s
rook-ceph-mon-c   1         1         1            1           2m5s
rook-ceph-osd-0   1         1         1            1           95s
rook-ceph-osd-1   1         1         1            1           94s
rook-ceph-osd-2   1         1         1            1           93s
```

Ceph Dashboard 를 외부에서 접속할 수 있게 해주는 Service 객체를 생성합니다.

**rook/dashboard-external-http.yaml**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rook-ceph-mgr-dashboard-external-http
  namespace: rook-ceph
  labels:
    app: rook-ceph-mgr
    rook_cluster: rook-ceph
spec:
  ports:
  - name: dashboard
    port: 7000
    protocol: TCP
    targetPort: 7000
  selector:
    app: rook-ceph-mgr
    rook_cluster: rook-ceph
  sessionAffinity: None
  type: LoadBalancer
```

LoadBalancer 를 이용해 외부 서비스용 IP 를 Dashboard 에 부여합니다.

```bash
kubectl create -f rook/dashboard-external-http.yaml

service/rook-ceph-mgr-dashboard-external-http created
```

생성한 Service 객체를 확인합니다.

```bash
kubectl get svc -n rook-ceph

NAME                                    TYPE           CLUSTER-IP       EXTERNAL-IP    PORT(S)          AGE
rook-ceph-mgr                           ClusterIP      10.107.101.123   <none>         9283/TCP         17m
rook-ceph-mgr-dashboard                 ClusterIP      10.111.254.202   <none>         7000/TCP         17m
rook-ceph-mgr-dashboard-external-http   LoadBalancer   10.111.106.222   10.254.1.152   7000:32346/TCP   11m
rook-ceph-mon-a                         ClusterIP      10.110.197.249   <none>         6790/TCP         18m
rook-ceph-mon-b                         ClusterIP      10.96.137.141    <none>         6790/TCP         18m
rook-ceph-mon-c                         ClusterIP      10.107.126.92    <none>         6790/TCP         17m
```



## Create Shared File System

Kubernetes 에 배포할 어플리케이션이 사용할 파일 시스템을 생성합니다. Shared File System 은 여러 Pod 에서 동시에 접근이 가능합니다.

**rook/filesystem.yaml**

```yaml
apiVersion: ceph.rook.io/v1beta1
kind: Filesystem
metadata:
  name: k8s-fs
  namespace: rook-ceph
spec:
  metadataPool:
    replicated:
      size: 2
  dataPools:
    - failureDomain: osd
      replicated:
        size: 2
  metadataServer:
    activeCount: 1
    activeStandby: true
    placement:
    resources:
```

k8s-fs 이름을 가진 File System 을 생성합니다.

```bash
kubectl create -f rook/filesystem.yaml

filesystem.ceph.rook.io/k8s-fs created
```

생성한 File System 을 Ceph Dashboard 화면에서 확인할 수 있습니다.

![ceph-dashboard-fs](./assets/ceph-dashboard-fs.png)



## Create Block Storage

Block storage 를 사용하기 위해 **StorageClass** 를 등록합니다. StorageClass 는 Kubernetes 가 Rook 을 통해 PersistentVolume 을 생성할 때 사용합니다.

**rook/storageclass.yaml**

```yaml
apiVersion: ceph.rook.io/v1beta1
kind: Pool
metadata:
  name: replicapool
  namespace: rook-ceph
spec:
  replicated:
    size: 2
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
   name: rook-ceph-block
provisioner: ceph.rook.io/block
parameters:
  pool: replicapool
  clusterNamespace: rook-ceph
  fstype: xfs
```

위에서 지정한 Replicapool 은 두 개의 복제본을 유지합니다.

```bash
kubectl create -f rook/storageclass.yaml

pool.ceph.rook.io/replicapool created
storageclass.storage.k8s.io/rook-ceph-block created
```

Ceph Dashboard 에서 생성한 ReplicaPool 을 확인할 수 있습니다.

![ceph-replicapool](./assets/ceph-replicapool.png)



# Deploy Application with Ceph

## Deploy Minio

Minio 어플리케이션을 Shared File System 과 함께 배포해보겠습니다.

배포하기 전에 File System 안에 사용할 디렉토리를 먼저 만드는 것이 필요합니다. 여기에서는 간단하게 nginx 컨테이너 내부 /tmp/fs 디렉토리에 Share File System 을 붙인 후에 디렉토리를 생성합니다.

```bash
kubectl create -f rook/nginx-fs-deploy.yaml

deployment.apps/nginx-fs created
```

실행된 Pod 이름을 확인합니다.

```bash
kubectl get pod

NAME                        READY   STATUS    RESTARTS   AGE
nginx-fs-5bfc8dbf5f-5ggz8   1/1     Running   0          77s
```

**kubectl exec** 명령을 이용해 앞에서 실행한 Pod 에 접속합니다.

```bash
rook$ kubectl exec -it nginx-fs-5bfc8dbf5f-5ggz8 /bin/bash
root@nginx-fs-5bfc8dbf5f-5ggz8:/# cd /tmp/fs
root@nginx-fs-5bfc8dbf5f-5ggz8:/tmp/fs# mkdir minio
root@nginx-fs-5bfc8dbf5f-5ggz8:/tmp/fs# exit
exit
```



**minio/minio-deploy.yaml**

```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: minio
spec:
  template:
    metadata:
      labels:
        k8s-app: minio
    spec:
      containers:
      - name: minio
        volumeMounts:
        - name: minio-store
          mountPath: "/data"
        image: minio/minio:RELEASE.2018-11-17T01-23-48Z
        args:
        - server
        - /data
        env:
        - name: MINIO_ACCESS_KEY
          value: "minio"
        - name: MINIO_SECRET_KEY
          value: "minio123"
        ports:
        - containerPort: 9000
      volumes:
      - name: minio-store
        flexVolume:
          driver: ceph.rook.io/rook
          fsType: ceph
          options:
            fsName: k8s-fs
            clusterNamespace: rook-ceph
            path: /minio
```

minio 를 클러스터에 배포합니다.

```bash
kubectl create -f minio/minio-deploy.yaml

deployment.extensions/minio created
```

```bash
kubectl create -f minio/minio-svc.yaml

service/minio-svc created
```



배포한 minio 저장소에 파일을 저장해보겠습니다.

![minio](./assets/minio.png)



## Deploy MySQL

MySQL 어플리케이션을 Block Storage 와 함께 배포해보겠습니다.

먼저 앞에서 생성한 StorageClass 이름으로 PersistentVolumeClaim 을 생성합니다.

**mysql/mysql-pvc.yaml**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
  labels:
    k8s-app: mysql
spec:
  storageClassName: rook-ceph-block
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

```bash
kubectl create -f mysql/mysql-pvc.yaml

persistentvolumeclaim/mysql-pvc created
```

MySQL 를 배포할 때 컨테이너에 앞에서 생성한 mysql-pvc 를 붙여줍니다.



**mysql/mysql-deploy.yaml**

```yaml
apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: mysql
  labels:
    k8s-app: mysql
spec:
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        k8s-app: mysql
    spec:
      containers:
      - image: mysql:5.7
        name: mysql
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: changeme
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: mysql-persistent-storage
          mountPath: /var/lib/mysql
      volumes:
      - name: mysql-persistent-storage
        persistentVolumeClaim:
          claimName: mysql-pvc
```

```bash
kubectl create -f mysql/mysql-deploy.yaml

deployment.apps/mysql created
```

```bash
kubectl create -f mysql/mysql-svc.yaml

service/mysql created
```



생성한 MySQL 서버에 접속하여 제대로 동작하고 있는지 확인해봅니다.

```bash
kubectl get svc

NAME         TYPE           CLUSTER-IP       EXTERNAL-IP    PORT(S)          AGE
kubernetes   ClusterIP      10.96.0.1        <none>         443/TCP          4h21m
minio-svc    LoadBalancer   10.101.22.31     10.254.1.153   9000:32719/TCP   3m46s
mysql        LoadBalancer   10.99.254.138    10.254.1.154   3306:31821/TCP   9s
nginx-svc    NodePort       10.101.189.208   <none>         80:31000/TCP     45m
```

IP 주소를 확인하고 mysql client 를 이용해 접속합니다.

```bash
mysql -uroot -p -h 10.254.1.154

Enter password:
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 3
Server version: 5.7.24 MySQL Community Server (GPL)

Copyright (c) 2000, 2018, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
+--------------------+
4 rows in set (0.00 sec)
```



## Deploy Ghost

Ghost 어플리케이션에서 사용할 디렉토리를 Share File System 에 미리 생성해둡니다.

```bash
kubectl exec -it nginx-fs-5bfc8dbf5f-5ggz8 /bin/bash

root@nginx-fs-5bfc8dbf5f-5ggz8:/# cd /tmp/fs
root@nginx-fs-5bfc8dbf5f-5ggz8:/tmp/fs# mkdir ghost
root@nginx-fs-5bfc8dbf5f-5ggz8:/tmp/fs# ls -al
total 4
drwxr-xr-x 1 root root    2 Nov 18 15:35 .
drwxrwxrwt 1 root root 4096 Nov 18 15:05 ..
drwxr-xr-x 1 root root    0 Nov 18 15:35 ghost
drwxr-xr-x 1 root root    2 Nov 18 15:15 minio
```

MySQL 에 접속하여 사용할 데이터베이스를 생성합니다.

```bash
mysql -uroot -p -h 10.254.1.153

Enter password:
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 4
Server version: 5.7.24 MySQL Community Server (GPL)

Copyright (c) 2000, 2018, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> create database ghost;
Query OK, 1 row affected (0.02 sec)
```



PersistentVolume 과 Database 생성을 완료한 후에 Ghost 어플리케이션을 배포합니다.

**ghost/ghost-deploy.yaml**

```yaml
apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: ghost
spec:
  template:
    metadata:
      labels:
        k8s-app: ghost
    spec:
      containers:
      - name: ghost
        volumeMounts:
        - name: ghost-volume
          mountPath: "/var/lib/ghost/content"
        image: ghost:2
        env:
        - name: database__client
          value: "mysql"
        - name: database__connection__host
          value: "mysql"
        - name: database__connection__user
          value: "root"
        - name: database__connection__database
          value: "ghost"
        - name: database__connection__password
          value: "changeme"
        ports:
        - containerPort: 2368
      volumes:
      - name: ghost-volume
        flexVolume:
          driver: ceph.rook.io/rook
          fsType: ceph
          options:
            fsName: k8s-fs
            clusterNamespace: rook-ceph
            path: /ghost
```

Ghost 어플리케이션을 배포합니다.

```bash
kubectl create -f ghost/ghost-deploy.yaml

deployment.apps/ghost created
```

외부에서 접속할 수 있도록 Service 를 생성합니다.

```bash
kubectl create -f ghost/ghost-svc.yaml

service/ghost-svc created
```

Ghost 어플리케이션이 배포된 것을 확인합니다.

```bash
kubectl get deploy ghost

NAME    DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
ghost   1         1         1            1           6m9s
```



배포가 완료된 후 LoadBalancer IP 로 접속하여 확인합니다.

![ghost](./assets/ghost.png)

MySQL 에 테이블이 제대로 생성되었는지 확인해봅니다.

```bash
mysql -uroot -p -h 10.254.1.153

Enter password:
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 350
Server version: 5.7.24 MySQL Community Server (GPL)

Copyright (c) 2000, 2018, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> use ghost;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
mysql> show tables;
+------------------------+
| Tables_in_ghost        |
+------------------------+
| accesstokens           |
| api_keys               |
| app_fields             |
| app_settings           |
| apps                   |
| brute                  |
| client_trusted_domains |
| clients                |
| integrations           |
| invites                |
| migrations             |
| migrations_lock        |
| mobiledoc_revisions    |
| permissions            |
| permissions_apps       |
| permissions_roles      |
| permissions_users      |
| posts                  |
| posts_authors          |
| posts_tags             |
| refreshtokens          |
| roles                  |
| roles_users            |
| sessions               |
| settings               |
| subscribers            |
| tags                   |
| users                  |
| webhooks               |
+------------------------+
29 rows in set (0.00 sec)
```



# Summary

IDC 혹은 로컬 네트워크에서 **Kubernetes** 클러스터를 구축하고 사용할 경우에는 **Rook**, **Ceph**, **Metallb** 등을 활용하여 **Cloud Native** 한 환경을 구축해볼 수 있습니다. **Rook** 과 **Ceph** 를 이용해 특정 노드에 종속적인 **Persistent Volume** 을 생성하고 사용해야하는 제약을 극복할 수 있습니다.  마지막으로 **Metallb** 를 이용해 외부에서 Kubernetes 클러스터에 배포되어 있는 서비스를 연결하는데 도움을 받을 수 있습니다.

실습 내용에 대하여 부족하거나 보완해야할 점이 있다면 있다면 메일로 보내주세요. 감사합니다.

임찬식 (chanshik@gmail.com) 


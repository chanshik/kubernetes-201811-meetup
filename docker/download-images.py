import urllib.request
import sys

if len(sys.argv) == 1:
    print("Downloads saved docker images.")
    print("Usage: python3 [HOST]")
    sys.exit(1)

host = sys.argv[1]

docker_images = [
    "gcr.io_kubernetes-helm_tiller+v2.11.0.docker",
    "ghost+2.docker",
    "k8s.gcr.io_coredns+1.2.2.docker",
    "k8s.gcr.io_etcd+3.2.24.docker",
    "k8s.gcr.io_kube-apiserver+v1.12.2.docker",
    "k8s.gcr.io_kube-controller-manager+v1.12.2.docker",
    "k8s.gcr.io_kube-proxy+v1.12.2.docker",
    "k8s.gcr.io_kubernetes-dashboard-amd64+v1.10.0.docker",
    "k8s.gcr.io_kube-scheduler+v1.12.2.docker",
    "k8s.gcr.io_pause+3.1.docker",
    "metallb_controller+v0.7.3.docker",
    "metallb_speaker+v0.7.3.docker",
    "minio_minio+RELEASE.2018-11-17T01-23-48Z.docker",
    "mysql+5.7.docker",
    "nginx+latest.docker",
    "quay.io_calico_cni+v3.3.1.docker",
    "quay.io_calico_node+v3.3.1.docker",
    "redis+4.0.11-alpine.docker",
    "rook_ceph+v0.8.3.docker",
]

for docker_image in docker_images:
    url = "http://{}/{}".format(host, docker_image)

    print("Downloading {}".format(url))
    urllib.request.urlretrieve(url, docker_image)

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
        sudo cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb http://apt.kubernetes.io/ kubernetes-xenial main
EOF
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

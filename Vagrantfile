# pyinfra test VM's

Vagrant.configure('2') do |config|
    # Disable /vagrant synced folder
    config.vm.synced_folder '.', '/vagrant', disabled: true

    config.vm.provider 'virtualbox' do |v|
        v.memory = 256
    end

    # Disable updating/installing Virtualbox guest additions with vagrant-vbguest
    if Vagrant.has_plugin?('vagrant-vbguest')
        config.vbguest.auto_update = false
    end

    # Begin pyinfra test VM's:
    #

    config.vm.define :ubuntu16 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-16.04'
    end

    config.vm.define :ubuntu18 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-18.04'
        # uncomment the next line for examples/pxe_infra.py
        # ubuntu.vm.network "public_network", ip: "192.168.0.240"
        ubuntu.vm.provider 'virtualbox' do |v|
            v.memory = 384  # ubuntu18 is memory hungry
        end
    end

    config.vm.define :debian8 do |debian|
        debian.vm.box = 'bento/debian-8'
    end

    config.vm.define :debian9 do |debian|
        debian.vm.box = 'bento/debian-9'
    end

    config.vm.define :centos6 do |centos|
        centos.vm.box = 'bento/centos-6'
    end

    config.vm.define :centos7 do |centos|
        centos.vm.box = 'bento/centos-7'
    end

    config.vm.define :centos8 do |centos|
        centos.vm.box = 'bento/centos-8'
    end

    config.vm.define :fedora24 do |fedora|
        fedora.vm.box = 'bento/fedora-24'
    end

    config.vm.define :openbsd6 do |openbsd|
        openbsd.vm.box = 'generic/openbsd6'
    end
end

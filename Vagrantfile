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
        ubuntu.vm.provider 'virtualbox' do |v|
            v.memory = 384  # ubuntu18 is memory hungry
        end
    end

    config.vm.define :ubuntu20 do |ubuntu|
        ubuntu.vm.box = 'bento/ubuntu-20.04'
        ubuntu.vm.provider 'virtualbox' do |v|
            v.memory = 384  # ubuntu20 is memory hungry
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

    config.vm.define :freebsd12 do |openbsd|
        openbsd.vm.box = 'generic/freebsd12'
    end

    config.vm.define :windows2019 do |windows|
        windows.vm.box = 'StefanScherer/windows_2019'
        windows.vm.provider "vmware_desktop" do |v|
            v.vmx["memsize"] = "1024"
            v.vmx["numvcpus"] = "2"
            v.gui = true
       end
    end

    config.vm.define :windows10 do |windows|
        windows.vm.box = "StefanScherer/windows_10"
        windows.vm.provider "vmware_desktop" do |v|
            v.vmx["memsize"] = "1024"
            v.vmx["numvcpus"] = "2"
            v.gui = true
       end
    end

    config.vm.define :opensuse_leap15 do |opensuse|
        opensuse.vm.box = 'bento/opensuse-leap-15'
        opensuse.vm.box_version = "202006.17.0"
    end

    config.vm.define :opensuse_tumbleweed do |opensuse|
        opensuse.vm.box = "opensuse/Tumbleweed.x86_64"
        opensuse.vm.box_version = "1.0.20200618"
    end
end

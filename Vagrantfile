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

    # Linux test VMs
    #

    config.vm.define :ubuntu18 do |ubuntu|
        ubuntu.vm.box = 'generic/ubuntu1804'
        ubuntu.vm.provider 'virtualbox' do |v|
            v.memory = 384  # ubuntu18 is memory hungry
        end
    end

    config.vm.define :ubuntu20 do |ubuntu|
        ubuntu.vm.box = 'generic/ubuntu2004'
        ubuntu.vm.provider 'virtualbox' do |v|
            v.memory = 384  # ubuntu20 is memory hungry
        end
    end

    config.vm.define :debian9 do |debian|
        debian.vm.box = 'generic/debian9'
    end

    config.vm.define :debian10 do |debian|
        debian.vm.box = 'generic/debian10'
    end

    config.vm.define :centos7 do |centos|
        centos.vm.box = 'generic/centos7'
    end

    config.vm.define :centos8 do |centos|
        centos.vm.box = 'generic/centos8'
    end

    config.vm.define :fedora33 do |fedora|
        fedora.vm.box = 'generic/fedora33'
    end

    config.vm.define :alpine38 do |fedora|
        fedora.vm.box = 'generic/alpine38'
    end

    # BSD test VMs
    #

    config.vm.define :openbsd6 do |openbsd|
        openbsd.vm.box = 'generic/openbsd6'
    end

    config.vm.define :freebsd12 do |freebsd|
        freebsd.vm.box = 'generic/freebsd12'
    end

    config.vm.define :netbsd9 do |netbsd|
        netbsd.vm.box = 'generic/netbsd9'
    end

    config.vm.define :hardenedbsd11 do |hardenedbsd|
        hardenedbsd.vm.box = 'generic/hardenedbsd11'
    end

    # Windows test VMs
    #

    config.vm.define :windows2019 do |windows|
        windows.vm.box = 'StefanScherer/windows_2019'
        windows.vm.provider 'vmware_desktop' do |v|
            v.vmx['memsize'] = '1024'
            v.vmx['numvcpus'] = '2'
            v.gui = true
       end
    end

    config.vm.define :windows10 do |windows|
        windows.vm.box = 'StefanScherer/windows_10'
        windows.vm.provider 'vmware_desktop' do |v|
            v.vmx['memsize'] = '1024'
            v.vmx['numvcpus'] = '2'
            v.gui = true
       end
    end

    # OpenSUSE test VMs
    #

    config.vm.define :opensuse_leap15 do |opensuse|
        opensuse.vm.box = 'bento/opensuse-leap-15'
    end

    config.vm.define :opensuse_tumbleweed do |opensuse|
        opensuse.vm.box = 'opensuse/Tumbleweed.x86_64'
    end
end

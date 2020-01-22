./do.py up

# TODO: improve sleep
sleep 60

./do.py list

# create do inventories
./do.py create

./test_do_adhocs.bats
./test_do_deploy.bats

cd puppet
./test_step0.bats
./test_step1.bats
./test_step2.bats
./test_step3.bats
./test_post.bats
cd ..

./do.py down

sleep 10

./do.py list

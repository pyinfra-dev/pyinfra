line=`ip addr | grep 'inet 10.'`
if [ $? -eq 0 ];
then
   net=`echo $line | awk '{ print $2 }'`
   ip addr del $net dev eth0
fi

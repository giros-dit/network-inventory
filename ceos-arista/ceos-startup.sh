echo "ceos1 Arista cEOS router startup configuration:"
echo "-> Uploading NETCONF management protocol configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/netconf-config-ceos1 ceos1:/mnt/flash/startup-config
docker exec -it ceos1 Cli -p 15 -c "copy start run"
echo "-> Checking NETCONF configuration status..."
sleep 2
docker exec -it ceos1 Cli -p 15 -c "show management api netconf"
echo "-> Uploading gNMI management protocol configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/gnmi-config-ceos1 ceos1:/mnt/flash/startup-config
docker exec -it ceos1 Cli -p 15 -c "copy start run"
echo "-> Checking gNMI configuration status..."
sleep 6
docker exec -it ceos1 Cli -p 15 -c "show management api gnmi"
echo "-> Uploading addressing configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/addressing-config-ceos1 ceos1:/mnt/flash/startup-config
docker exec -it ceos1 Cli -p 15 -c "copy start run"
echo "-> Checking addressing configuration..."
sleep 1
docker exec -it ceos1 Cli -p 15 -c "show running-config section interface"

echo ""

echo "ceos2 Arista cEOS router startup configuration:"
echo "-> Uploading NETCONF management protocol configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/netconf-config-ceos2 ceos2:/mnt/flash/startup-config
docker exec -it ceos2 Cli -p 15 -c "copy start run"
echo "-> Checking NETCONF configuration status..."
sleep 2
docker exec -it ceos2 Cli -p 15 -c "show management api netconf"
echo "-> Uploading gNMI management protocol configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/gnmi-config-ceos2 ceos2:/mnt/flash/startup-config
docker exec -it ceos2 Cli -p 15 -c "copy start run"
echo "-> Checking gNMI configuration status..."
sleep 6
docker exec -it ceos2 Cli -p 15 -c "show management api gnmi"
echo "-> Uploading addressing configuration..."
sleep 0.5
docker cp ../ceos-arista/ceos-startup-config/addressing-config-ceos2 ceos2:/mnt/flash/startup-config
docker exec -it ceos2 Cli -p 15 -c "copy start run"
echo "-> Checking addressing configuration..."
sleep 1
docker exec -it ceos2 Cli -p 15 -c "show running-config section interface"

import logging
import csv
import socket

from random import shuffle, randint, choice, uniform

from lea import Lea

from Attack import BaseAttack
from Attack.AttackParameters import Parameter as Param
from Attack.AttackParameters import ParameterTypes

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
# noinspection PyPep8
from scapy.layers.inet import IP, Ether, TCP


class PortscanAttack(BaseAttack.BaseAttack):
    # Aidmar
    def get_ports_from_nmap_service_dst(self, ports_num):
        """
        Read the most ports_num frequently open ports from nmap-service-tcp file to be used in Portscan attack.

        :return: Ports numbers to be used as default dest ports or default open ports in Portscan attack.
        """
        ports_dst = []
        spamreader = csv.reader(open('nmap-services-tcp.csv', 'rt'), delimiter=',')
        for count in range(ports_num):
            # escape first row (header)
            next(spamreader)
            # save ports numbers
            ports_dst.append(next(spamreader)[0])
        # shuffle ports numbers
        if(ports_num==1000): # used for port.dst
            temp_array = [[0 for i in range(10)] for i in range(100)]
            port_dst_shuffled = []
            for count in range(0, 9):
                temp_array[count] = ports_dst[count * 100:count * 100 + 99]
                shuffle(temp_array[count])
                port_dst_shuffled += temp_array[count]
        else: # used for port.open
            port_dst_shuffled = shuffle(ports_dst)
        return port_dst_shuffled


    def is_valid_ip_address(self,addr):
        """
        Check if the IP address family is suported.

        :param addr: IP address to be checked
        :return: Boolean
        """
        try:
            socket.inet_aton(addr)
            return True
        except socket.error:
            return False

    def __init__(self, statistics, pcap_file_path):
        """
        Creates a new instance of the PortscanAttack.

        :param statistics: A reference to the statistics class.
        """
        # Initialize attack
        super(PortscanAttack, self).__init__(statistics, "Portscan Attack", "Injects a nmap 'regular scan'",
                                             "Scanning/Probing")

        # Define allowed parameters and their type
        self.supported_params = {
            Param.IP_SOURCE: ParameterTypes.TYPE_IP_ADDRESS,
            Param.IP_DESTINATION: ParameterTypes.TYPE_IP_ADDRESS,
            Param.PORT_SOURCE: ParameterTypes.TYPE_PORT,
            Param.PORT_DESTINATION: ParameterTypes.TYPE_PORT,
            Param.PORT_OPEN: ParameterTypes.TYPE_PORT,
            Param.MAC_SOURCE: ParameterTypes.TYPE_MAC_ADDRESS,
            Param.MAC_DESTINATION: ParameterTypes.TYPE_MAC_ADDRESS,
            Param.INJECT_AT_TIMESTAMP: ParameterTypes.TYPE_FLOAT,
            Param.INJECT_AFTER_PACKET: ParameterTypes.TYPE_PACKET_POSITION,
            Param.PORT_DEST_SHUFFLE: ParameterTypes.TYPE_BOOLEAN,
            Param.PORT_DEST_ORDER_DESC: ParameterTypes.TYPE_BOOLEAN,
            Param.IP_SOURCE_RANDOMIZE: ParameterTypes.TYPE_BOOLEAN,
            Param.PACKETS_PER_SECOND: ParameterTypes.TYPE_FLOAT,
            Param.PORT_SOURCE_RANDOMIZE: ParameterTypes.TYPE_BOOLEAN
        }

        # PARAMETERS: initialize with default values
        # (values are overwritten if user specifies them)
        most_used_ip_address = self.statistics.get_most_used_ip_address()
        if isinstance(most_used_ip_address, list):
            most_used_ip_address = most_used_ip_address[0]

        self.add_param_value(Param.IP_SOURCE, most_used_ip_address)
        self.add_param_value(Param.IP_SOURCE_RANDOMIZE, 'False')
        self.add_param_value(Param.MAC_SOURCE, self.statistics.get_mac_address(most_used_ip_address))

        random_ip_address = self.statistics.get_random_ip_address()
        # Aidmar
        while not self.is_valid_ip_address(random_ip_address):
            random_ip_address = self.statistics.get_random_ip_address()

        self.add_param_value(Param.IP_DESTINATION, random_ip_address)
        destination_mac = self.statistics.get_mac_address(random_ip_address)
        if isinstance(destination_mac, list) and len(destination_mac) == 0:
            destination_mac = self.generate_random_mac_address()
        self.add_param_value(Param.MAC_DESTINATION, destination_mac)

        self.add_param_value(Param.PORT_DESTINATION, self.get_ports_from_nmap_service_dst(1000))
        #self.add_param_value(Param.PORT_DESTINATION, '1-1023,1720,1900,8080,56652')

        # Not used initial value
        self.add_param_value(Param.PORT_OPEN, '1,11,111,1111')

        self.add_param_value(Param.PORT_DEST_SHUFFLE, 'False')
        self.add_param_value(Param.PORT_DEST_ORDER_DESC, 'False')

        self.add_param_value(Param.PORT_SOURCE, randint(1024, 65535))
        self.add_param_value(Param.PORT_SOURCE_RANDOMIZE, 'False')

        self.add_param_value(Param.PACKETS_PER_SECOND,
                             (self.statistics.get_pps_sent(most_used_ip_address) +
                              self.statistics.get_pps_received(most_used_ip_address)) / 2)
        self.add_param_value(Param.INJECT_AFTER_PACKET, randint(0, self.statistics.get_packet_count()))

    def generate_attack_pcap(self):
        def update_timestamp(timestamp, pps, maxdelay):
            """
            Calculates the next timestamp to be used based on the packet per second rate (pps) and the maximum delay.

            :return: Timestamp to be used for the next packet.
            """
            return timestamp + uniform(0.1 / pps, maxdelay)


        # Determine ports
        dest_ports = self.get_param_value(Param.PORT_DESTINATION)
        if self.get_param_value(Param.PORT_DEST_ORDER_DESC):
            dest_ports.reverse()
        elif self.get_param_value(Param.PORT_DEST_SHUFFLE):
            shuffle(dest_ports)
        if self.get_param_value(Param.PORT_SOURCE_RANDOMIZE):
            # Aidmar
            sport = randint(1, 65535)
            #sport = randint(0, 65535)
        else:
            sport = self.get_param_value(Param.PORT_SOURCE)

        # Timestamp
        timestamp_next_pkt = self.get_param_value(Param.INJECT_AT_TIMESTAMP)
        # store start time of attack
        self.attack_start_utime = timestamp_next_pkt

        # Initialize parameters
        packets = []
        ip_source = self.get_param_value(Param.IP_SOURCE)
        ip_destination = self.get_param_value(Param.IP_DESTINATION)
        mac_source = self.get_param_value(Param.MAC_SOURCE)
        mac_destination = self.get_param_value(Param.MAC_DESTINATION)
        pps = self.get_param_value(Param.PACKETS_PER_SECOND)
        randomdelay = Lea.fromValFreqsDict({1 / pps: 70, 2 / pps: 30, 5 / pps: 15, 10 / pps: 3})
        maxdelay = randomdelay.random()

        # open ports
        # Aidmar
        ports_open = self.get_param_value(Param.PORT_OPEN)
        if ports_open == [1,11,111,1111]:  # user did not define open ports
            # the ports that were already used by ip.dst (direction in) in the background traffic are open ports
            ports_used_by_ip_dst = self.statistics.process_db_query(
                "SELECT portNumber FROM ip_ports WHERE portDirection='in' AND ipAddress='" + ip_destination + "';")
            if ports_used_by_ip_dst:
                ports_open = ports_used_by_ip_dst
            else: # if no ports were retrieved from database
                ports_open = self.get_ports_from_nmap_service_dst(randint(0,10))
            #print("\nPorts used by %s: %s" % (ip_destination, ports_open))
        # in case of one open port, convert ports_open to array
        if not isinstance(ports_open, list):
            ports_open = [ports_open]
        # =========================================================================================================


        # MSS (Maximum Segment Size) for Ethernet. Allowed values [536,1500]
        # Aidmar
        # mss = self.statistics.get_mss(ip_destination)
        mss_dst = self.statistics.get_mss(ip_destination)
        mss_src = self.statistics.get_mss(ip_source)
        # =========================================================================================================

        # Set TTL based on TTL distribution of IP address
        ttl_dist = self.statistics.get_ttl_distribution(ip_source)
        if len(ttl_dist) > 0:
            ttl_prob_dict = Lea.fromValFreqsDict(ttl_dist)
            ttl_value = ttl_prob_dict.random()
        else:
            ttl_value = self.statistics.process_db_query("most_used(ttlValue)")


        for dport in dest_ports:
            # Parameters changing each iteration
            if self.get_param_value(Param.IP_SOURCE_RANDOMIZE) and isinstance(ip_source, list):
                ip_source = choice(ip_source)

            # 1) Build request package
            request_ether = Ether(src=mac_source, dst=mac_destination)
            request_ip = IP(src=ip_source, dst=ip_destination, ttl=ttl_value)
            # Aidmar - random src port for each packet
            sport = randint(1, 65535)
            if mss_src is None:
                request_tcp = TCP(sport=sport, dport=dport, flags='S')
            else:
                request_tcp = TCP(sport=sport, dport=dport, flags='S', options=[('MSS', mss_src)])
            # =========================================================================================================

            request = (request_ether / request_ip / request_tcp)
            # first packet uses timestamp provided by attack parameter Param.INJECT_AT_TIMESTAMP
            if len(packets) > 0:
                timestamp_next_pkt = update_timestamp(timestamp_next_pkt, pps, maxdelay)
            request.time = timestamp_next_pkt
            packets.append(request)

            # 2) Build reply package
            if dport in ports_open:  # destination port is OPEN
                reply_ether = Ether(src=mac_destination, dst=mac_source)
                reply_ip = IP(src=ip_destination, dst=ip_source, flags='DF')
                if mss_dst is None:
                    reply_tcp = TCP(sport=dport, dport=sport, seq=0, ack=1, flags='SA', window=29200)
                else:
                    reply_tcp = TCP(sport=dport, dport=sport, seq=0, ack=1, flags='SA', window=29200,
                                    options=[('MSS', mss_dst)])
                reply = (reply_ether / reply_ip / reply_tcp)
                timestamp_next_pkt = update_timestamp(timestamp_next_pkt, pps, maxdelay)
                reply.time = timestamp_next_pkt
                packets.append(reply)

                # requester confirms
                confirm_ether = request_ether
                confirm_ip = request_ip
                confirm_tcp = TCP(sport=sport, dport=dport, seq=1, window=0, flags='R')
                reply = (confirm_ether / confirm_ip / confirm_tcp)
                timestamp_next_pkt = update_timestamp(timestamp_next_pkt, pps, maxdelay)
                reply.time = timestamp_next_pkt
                packets.append(reply)

                # else: destination port is NOT OPEN -> no reply is sent by target

        # store end time of attack
        self.attack_end_utime = packets[-1].time

        # write attack packets to pcap
        pcap_path = self.write_attack_pcap(sorted(packets, key=lambda pkt: pkt.time))

        # return packets sorted by packet time_sec_start
        return len(packets), pcap_path

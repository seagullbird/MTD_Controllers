from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from MTD_server import MTDServer
from factory import messages as msgFactory
from factory import packets as pktFactory
from ryu.lib import hub
from vid.vid import Vid
import socket


class UltravagServerProxy(app_manager.RyuApp):
    VID_UPDATE_RATE = 30
    NETWORK_INIT_TIME = 80
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(UltravagServerProxy, self).__init__(*args, **kwargs)
        self.server = MTDServer()
        self._print_routing_tables()
        # start vid updating
        self.vid_update_thread = hub.spawn(self._vid_update)
        # start tcp listening
        self.tcp_listen_thread = hub.spawn(self._tcp_listen)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 65535, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        eth_type = eth.ethertype
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        in_port = msg.match['in_port']

        self.logger.info("PacketIn: Ethertype ==== %s, dst ==== %s, src ==== %s", eth_type, dst, src)

        if eth_type == ether_types.ETH_TYPE_ARP:
            arpp = pkt.get_protocol(arp.arp)
            src_ip = arpp.src_ip
            src_mac = src
            dst_ip = arpp.dst_ip
            if src_ip != dst_ip:
                self._handle_arp(datapath, in_port, src_mac, src_ip, dst_ip)
            else:
                self._handle_host_register(datapath, in_port, src_mac, src_ip, dst_ip)

    def _handle_arp(self, datapath, in_port, src_mac, src_ip, dst_ip):
        self.logger.info("Handling ARP...")
        # arp askee
        dst_host = self.server.find_host_by_ip(dst_ip)
        self.logger.info("ARP askee is: %s", str(dst_host))
        # arp asker
        src_host = self.server.find_host_by_fake_mac(src_mac)
        self.logger.info("ARP asker is: %s", str(src_host))
        if dst_host and src_host:
            if self.server.add_host_forwarding_entry(src_host.switch.dpid, dst_host):
                self.logger.info("Adding new host forwarding entry to %s, host.fake_mac == %s", src_host.dpid, dst_host.fake_mac)

            dst_mac = dst_host.fake_mac
            src_mac = Vid.vid2mac(src_host.switch.vid.sw, src_host.vid.host)
            self.logger.info('PacketIn: ARP, %s is asking for %s', src_ip, dst_ip)
            self._send_arp_reply(datapath, in_port, dst_mac, src_mac, dst_ip, src_ip)
            self.logger.info('Answer ARP for %s with MAC address %s', dst_ip, dst_mac)

    def _handle_host_register(self, datapath, in_port, src_mac, src_ip, dst_ip):
        # proxy is registering
        # src_mac should be the hwaddr of host
        host = self.server.get_host(src_mac)
        if host:
            # host is registering its first vid
            self.logger.info('Vid register request received from %s', host.local_mac)
            self.server.register_host(host)
            self.server.add_host_receiving_entry(host)
            src_mac = host.fake_mac
            dst_mac = Vid.vid2mac(host.switch.vid.sw, host.vid.host)
            self._send_arp_reply(datapath, in_port, src_mac, dst_mac, src_ip, dst_ip)

            self.logger.info('Answer host register with vid %s', src_mac)
            # self.server.mod_arp_request_flow(host.dpid)

    def _handle_host_update(self, sock, ip_addr):
        host = self.server.topo.find_host_by_ip(ip_addr)
        if host:
            self.logger.info('\nVid update request received from %s', host.fake_mac)
            # modify flows
            affected_dpids = self.server.answer_host_vid_update_request(host)
            # update arp in 192.168.0.1
            self.server.set_local_arp_table(host.ip, host.fake_mac)
            # answer update request
            sock.send('message: ' + host.fake_mac)
            self.logger.info('Answer host update request with vid %s\n', host.fake_mac)
            # inform hosts
            for dpid in affected_dpids:
                for host in self.server.topo.switches[dpid].hosts.itervalues():
                    if hasattr(host, 'sock'):
                        host.sock.send('message: flush your arp')

    def _send_arp_reply(self, datapath, port, src_mac, dst_mac, src_ip, dst_ip):
        arp_answer_pkt = pktFactory.arp_answer_packet(src_mac, src_ip, dst_mac, dst_ip)
        msg = msgFactory.packet_out(datapath, port, arp_answer_pkt)
        datapath.send_msg(msg)

    def _print_routing_tables(self):
        for switch in self.server.topo.switches.itervalues():
            self.logger.info("%s", str(switch.rt))

    def _vid_update(self):
        hub.sleep(self.NETWORK_INIT_TIME)
        while True:
            hub.sleep(self.VID_UPDATE_RATE)
            self.logger.info("Updating Vids.")
            self.server.exec_vid_update()
            self._print_routing_tables()

    def _tcp_listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('192.168.0.1', 6666))
        s.listen(0)
        while True:
            ss, addr = s.accept()
            hub.spawn(self._handle_tcp_connect, sock=ss, ip_addr=addr[0])

    def _handle_tcp_connect(self, sock, ip_addr):
        self.logger.info("Connection from: %s", ip_addr)
        self.server.add_host_sock(sock, ip_addr)
        while True:
            data = sock.recv(512).decode()
            if data == 'hid update':
                self._handle_host_update(sock, ip_addr)

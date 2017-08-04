from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event
from ryu.lib import hub
from utils import *
from random import randint
import socket


class UltravagProxy(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    MAX_VID_UPDATE_RATE = 50
    MIN_VID_UPDATE_RATE = 100
    server_ip_addr = '192.168.0.1'
    server_port = 6666

    def __init__(self, *args, **kwargs):
        super(UltravagProxy, self).__init__(*args, **kwargs)
        self.local_mac = getLocalMac('veth1')
        self.local_ip = getLocalIp('veth1')

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        datapath = ev.switch.dp
        self.datapath = datapath
        ports = ev.switch.ports
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for port in ports:
            if port.to_dict()['hw_addr'] == self.local_mac:
                self.inner_port = int(port.to_dict()['port_no'])
            else:
                self.outer_port = int(port.to_dict()['port_no'])
        self.register_thread = hub.spawn(self.register)

    def register(self):
        # set arp rule
        self._add_arp_rule(self.datapath)
        self._send_hid_request(self.local_mac, self.datapath)

    def _add_arp_rule(self, datapath):
        match = datapath.ofproto_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_spa=self.local_ip, arp_tpa=self.local_ip)
        actions = [datapath.ofproto_parser.OFPActionOutput(datapath.ofproto.OFPP_CONTROLLER)]
        add_flow(datapath, match, actions)

    def _add_routing_rules(self, datapath, parser, ofproto):
        # routing in
        match = parser.OFPMatch(in_port=self.outer_port)
        actions = [parser.OFPActionSetField(eth_dst=self.local_mac), parser.OFPActionOutput(self.inner_port)]
        add_flow(datapath=datapath, match=match, actions=actions, priority=65534)
        # routing out
        match = parser.OFPMatch(in_port=self.inner_port)
        actions = [parser.OFPActionSetField(eth_src=self.fake_mac), parser.OFPActionOutput(self.outer_port)]
        add_flow(datapath=datapath, match=match, actions=actions, priority=65534)

    def _update_flow_rules(self, datapath, parser, ofproto):
        # remove arp rule
        msg = clear_routing_table(datapath)
        datapath.send_msg(msg)
        # set up routing rules
        self._add_routing_rules(datapath=datapath, parser=parser, ofproto=ofproto)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        eth_type = eth.ethertype

        if eth_type == ether_types.ETH_TYPE_ARP:
            arpp = pkt.get_protocol(arp.arp)
            # register reply
            self.fake_mac = arpp.src_mac
            self.logger.info("Vid received: %s", self.fake_mac)
            self._update_flow_rules(datapath, parser, ofproto)
            # tcp connect to server
            self._handle_tcp_connect()
            self.vid_update_thread = hub.spawn(self._vid_update)
            hub.spawn(self._handle_flush_recv)
            hub.spawn(self._handle_update_recv)

    def _send_hid_request(self, src_mac, datapath):
        # send an arp packet
        dst_mac = 'ff:ff:ff:ff:ff:ff'
        src_ip = self.local_ip
        dst_ip = self.local_ip
        pkt = register_pkt(src_mac=src_mac, dst_mac=dst_mac, src_ip=src_ip, dst_ip=dst_ip)
        msg = register_msg(datapath, self.outer_port, pkt)
        datapath.send_msg(msg)
        self.logger.info("Sending hid request.")

    def _handle_tcp_connect(self):
        self.update_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.flush_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger.info("Connecting to server.")
        self.update_sock.connect((self.server_ip_addr, self.server_port))
        self.flush_sock.connect((self.server_ip_addr, self.server_port))
        self.logger.info("Server connected.")

    def _vid_update(self):
        while True:
            hub.sleep(randint(self.MAX_VID_UPDATE_RATE, self.MIN_VID_UPDATE_RATE))
            self.logger.info("Sending hid update request.")
            self.update_sock.send('hid update')

    def _handle_flush_recv(self):
        while True:
            data = self.flush_sock.recv(512).decode()
            msg = data.split(': ')[1]
            if msg == 'flush your arp':
                self.logger.info("Flushing ARP table...")
                flush_local_arp_table()
            else:
                self.logger.info("Invalid msg received from flush socket: %s", msg)


    def _handle_update_recv(self):
        while True:
            data = self.update_sock.recv(512).decode()
            msg = data.split(': ')[1]
            if is_MAC_address(msg):
                self.logger.info("New hid received: %s", msg)
                self.fake_mac = msg
                self._update_flow_rules(self.datapath, self.datapath.ofproto_parser, self.datapath.ofproto)
            else:
                self.logger.info("Invalid msg received from update socket: %s", msg)

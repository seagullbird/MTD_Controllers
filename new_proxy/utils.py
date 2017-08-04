import os
import netifaces
from ryu.lib.packet import arp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import packet


def getLocalMac(ifname):
    return netifaces.ifaddresses(ifname)[netifaces.AF_PACKET][0]['addr'].__str__()


def getLocalIp(ifname):
    return netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr'].__str__()


def add_flow(datapath, match, actions, priority=65535):
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    msg = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
    datapath.send_msg(msg)


def register_pkt(src_mac, dst_mac, src_ip, dst_ip):
    pkt = packet.Packet()
    eth = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
    arpp = arp.arp(opcode=arp.ARP_REQUEST, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip)
    pkt.add_protocol(eth)
    pkt.add_protocol(arpp)
    pkt.serialize()
    return pkt.data


def register_msg(datapath, port, pkt):
    ofproto = datapath.ofproto
    ofp = datapath.ofproto_parser
    actions = [ofp.OFPActionOutput(port)]
    buffer_id = 0xffffffff
    in_port = ofproto.OFPP_CONTROLLER
    msg = ofp.OFPPacketOut(datapath, buffer_id, in_port, actions, pkt)
    return msg


def clear_routing_table(datapath):
    ofproto = datapath.ofproto
    ofp = datapath.ofproto_parser
    match = ofp.OFPMatch()
    msg = ofp.OFPFlowMod(datapath=datapath, match=match, command=ofproto.OFPFC_DELETE, out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY, table_id=0, instructions=[])
    return msg


def flush_local_arp_table():
    os.system("ip neigh flush dev veth1")


def is_MAC_address(addr):
    try:
        for byte in addr.split(':'):
            if 0x00 > int(byte, 16) or 0xff < int(byte, 16):
                return False
        return True
    except:
        return False

from ryu.lib.packet import arp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import packet


def arp_answer_packet(src_mac, src_ip, dst_mac, dst_ip):
    pkt = packet.Packet()
    eth = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
    arpp = arp.arp_ip(opcode=arp.ARP_REPLY, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip)
    pkt.add_protocol(eth)
    pkt.add_protocol(arpp)
    pkt.serialize()
    return pkt.data


def sever_register_packet(src_mac, src_ip, dst_mac, dst_ip):
    pkt = packet.Packet()
    eth = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
    arpp = arp.arp_ip(opcode=arp.ARP_REQUEST, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip)
    pkt.add_protocol(eth)
    pkt.add_protocol(arpp)
    pkt.serialize()
    return pkt.data


def inform_hosts_packet(dst_mac):
    pkt = packet.Packet()
    eth = ethernet.ethernet(dst=dst_mac, ethertype=0x6666)
    pkt.add_protocol(eth)
    return pkt

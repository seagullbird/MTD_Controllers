from topo.topology import Topology
from topo.switch import Switch
from vid.vid import Vid
from utils import *
import os


class MTDServer(object):
    DPID = 32
    PORT = 1
    vid = Vid(0x00, 0x00)
    """Ultravag server app"""
    def __init__(self):
        # init topology and set ip links
        self.topo = Topology(links=getStats.get_topo_links())
        # init switches and set up flows in table 0
        self._init_switches()
        # build routing tables
        self._build_routing_tables()
        # write MTD edge switch flow
        self._enable_network_access()

    def _init_switches(self):
        self.dpids = getStats.get_dpids()
        for dpid in self.dpids:
            vid = Vid(sw=dpid, host=0x00)
            switch = Switch(dpid=dpid, vid=vid)
            if dpid == self.DPID:
                self.switch = switch
            self.topo.addSwitch(switch)
            # table 0
            # handle arp request
            if Switch.is_edge_switch(dpid):
                postFlows.add_arp_request_flow(dpid, Vid.vid2mac(0x20, 0x00))
                postFlows.add_arp_dir_transfer_flow(dpid, Vid.vid2mac(0x20, 0x00))
            # disable lldp
            postFlows.add_lldp_disable_flow(dpid)
            # rule for packet from hosts
            postFlows.add_host_packet_modify_flow(dpid)
            # set go to table 2
            postFlows.add_resubmit_flow(dpid, table_id=0, goto_id=2)

    def _enable_network_access(self):
        postFlows.add_host_receiving_flow(self.DPID, self.vid, self.PORT)

    def get_host(self, mac_addr):
        host = self.find_host_by_fake_mac(mac_addr)
        if host:
            return host
        return getStats.get_host(mac_addr)

    def register_host(self, host):
        host.update_vid(Vid.get_next_host_vid())
        host.set_fake_mac(Vid.vid2mac(host.vid.sw, host.vid.host))
        self.topo.switches[host.dpid].addHost(host)

    def add_host_receiving_entry(self, host):
        # table 3
        postFlows.add_host_receiving_flow(host.dpid, host.vid, host.port)

    def add_host_forwarding_entry(self, dpid, host):
        # table 1
        if self.topo.switches[dpid].add_host_forwarding_entry(host):
            postFlows.add_host_forwarding_flow(dpid, host.vid, host.switch.vid)
            return True
        return False

    def _build_routing_tables(self):
        self.topo.constructRT()
        self._push_routing_tables()

    def _push_routing_tables(self):
        for switch in self.topo.switches.itervalues():
            # table 2: routing table
            # set go to table 3 (host receiving table)
            postFlows.add_goto_table3_flow(switch.dpid, switch.vid)
            for level, entry in switch.rt.rtbl.iteritems():
                if level != 0 and entry['nexthop']:
                    postFlows.add_routing_table_flow(switch.dpid, entry['prefix'], entry['nexthop'][0])

    def _push_host_forwarding_tables(self):
        for switch in self.topo.switches.itervalues():
            # table 1: host forwarding table
            self._push_host_forwarding_table(switch)

    def _push_host_forwarding_table(self, switch):
        for host in switch.host_forwarding_table:
            self.add_host_forwarding_flow(switch.dpid, host.vid, host.switch.vid)

    def find_host_by_ip(self, ip):
        return self.topo.find_host_by_ip(ip)

    def find_host_by_fake_mac(self, fake_mac):
        return self.topo.find_host_by_fake_mac(fake_mac)

    def _clear_routing_tables(self):
        for dpid in self.dpids:
            postFlows.clear_routing_table(dpid, table_id=1)
            postFlows.clear_routing_table(dpid, table_id=2)

    def mod_arp_request_flows(self):
        for dpid in self.dpids:
            if Switch.is_edge_switch(dpid):
                self.mod_arp_request_flow(dpid)

    def del_arp_dir_transfer_flows(self):
        for dpid in self.dpids:
            if Switch.is_edge_switch(dpid):
                self.del_arp_dir_transfer_flow(dpid)

    def add_arp_dir_transfer_flows(self):
        for dpid in self.dpids:
            if Switch.is_edge_switch(dpid):
                self.add_arp_dir_transfer_flow(dpid)

    def mod_arp_request_flow(self, dpid):
        postFlows.mod_arp_request_flow(dpid, Vid.vid2mac(self.switch.vid.sw, self.vid.host))

    def del_arp_dir_transfer_flow(self, dpid):
        postFlows.del_arp_dir_transfer_flow(dpid, Vid.vid2mac(self.switch.vid.sw, self.vid.host))

    def add_arp_dir_transfer_flow(self, dpid):
        postFlows.add_arp_dir_transfer_flow(dpid, Vid.vid2mac(self.switch.vid.sw, self.vid.host))

    def del_host_receiving_flow(self, dpid, vid, port):
        postFlows.del_host_receiving_flow(dpid, vid, port)

    def add_host_forwarding_flow(self, dpid, host_vid, switch_vid):
        postFlows.add_host_forwarding_flow(dpid, host_vid, switch_vid)

    def del_host_forwarding_flow(self, dpid, host_vid, switch_vid):
        postFlows.del_host_forwarding_flow(dpid, host_vid, switch_vid)

    def exec_vid_update(self):
        self.del_arp_dir_transfer_flows()
        self.topo.updateRoutingPrefixes()
        # clear table 1, 2
        self._clear_routing_tables()
        # push table 2
        self._push_routing_tables()
        # push table 1
        self._push_host_forwarding_tables()
        # update server vid
        # change table 3 of server edge switch, matching server's new vid
        self.del_host_receiving_flow(self.DPID, self.vid, self.PORT)
        self.vid = Vid.get_next_host_vid()
        self._enable_network_access()
        self.add_arp_dir_transfer_flows()
        self.mod_arp_request_flows()

    def answer_host_vid_update_request(self, host):
        affected_dpids = []
        new_host_vid = Vid.get_next_host_vid()
        self.del_host_receiving_flow(host.dpid, host.vid, host.port)
        self.del_host_forwarding_flow(host.dpid, host.vid, host.switch.vid)

        for switch in self.topo.switches.itervalues():
            affected = False
            for h in switch.host_forwarding_table:
                if h.vid == host.vid:
                    affected = True
                    affected_dpids.append(switch.dpid)
                    h.vid = new_host_vid
            if affected:
                self.del_host_forwarding_flow(switch.dpid, host.vid, host.switch.vid)
                self.add_host_forwarding_flow(switch.dpid, new_host_vid, host.switch.vid)

        host.update_vid(new_host_vid)
        host.set_fake_mac(Vid.vid2mac(host.vid.sw, host.vid.host))
        self.add_host_receiving_entry(host)

        return affected_dpids

    def add_host_sock(self, sock, ip_addr):
        host = self.topo.find_host_by_ip(ip_addr)
        if host:
            host.set_sock(sock)

    def set_local_arp_table(self, ip_addr, new_mac_addr):
        os.system("sudo arp -s %s %s" % (ip_addr, new_mac_addr))

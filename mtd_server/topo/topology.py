from vid.strategy import Strategy
from vid.vid import Vid


class Topology(object):
    """network topology"""
    def __init__(self, links):
        # dpid - switch
        self.switches = {}
        self.links = links

    def addSwitch(self, new_switch):
        self.switches[new_switch.dpid] = new_switch

    def constructRT(self):
        # start with neighbors
        for src_dpid, dst_dpid, src_port_no in self.links:
            self.switches[src_dpid].neighbors[src_port_no] = self.switches[dst_dpid]
        for dpid in self.switches:
            self.switches[dpid].buildNeighborRT()

        # complete the rest gateways
        for switch_a in self.switches.values():
            for switch_b in self.switches.values():
                if switch_a == switch_b:
                    continue
                # judge if switch_a is switch_b's level-k gateway, if so, add a to the rt of b on level-k as the gateway
                levels = switch_b.isGateway(switch_a)
                if levels:
                    for level in levels:
                        switch_b.rt.addGateway(level, switch_a.vid)

        # build all nexthops
        for dpid in self.switches:
            self.switches[dpid].rt.buildNexthops()

    def updateRoutingPrefixes(self):
        prefixes = Strategy.genUpdatePrefixes()
        for spin_prefix in prefixes:
            for dpid in self.switches:
                rt = self.switches[dpid].rt
                for level in rt.rtbl:
                    route_prefix = rt.rtbl[level]['prefix']
                    if Strategy.match(route_prefix, spin_prefix):
                        rt.rtbl[level]['prefix'] = Strategy.spin(spin_prefix, route_prefix)
                self.switches[dpid].vid.update(rt.rtbl[0]['prefix'])
        return prefixes

    def find_host_by_ip(self, ip):
        for switch in self.switches.itervalues():
            for host in switch.hosts.itervalues():
                if host.ip == ip:
                    return host

    def find_host_by_fake_mac(self, fake_mac):
        for switch in self.switches.itervalues():
            for host in switch.hosts.itervalues():
                if host.fake_mac == fake_mac:
                    return host
        return

    def __str__(self):
        return str(self.switches)

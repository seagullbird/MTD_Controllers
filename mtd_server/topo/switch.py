from routing_table import RoutingTable


core_switches = [38, 42, 52, 56]


class Switch(object):
    """switches"""
    def __init__(self, dpid, vid):
        self.hosts = {}
        self.dpid = dpid
        self.vid = vid
        self.rt = RoutingTable(self.dpid, self.vid)
        # port_no - neighbor_switch
        self.neighbors = {}
        self.host_forwarding_table = {}

    @staticmethod
    def is_edge_switch(dpid):
        return dpid not in core_switches

    def addHost(self, host):
        self.hosts[host.local_mac] = host
        host.set_switch(self)

    def buildNeighborRT(self):
        if not self.neighbors:
            return

        # fill in neighbors first
        self.rt.fillInNeighbors(self.neighbors)

    def isGateway(self, switch_a):
        # Judge if switch_a is a level-k gateway of self. Return all possible levels
        levels = []
        distance = self.vid.getLevel(switch_a.vid)
        for neighbor_of_a in switch_a.neighbors.itervalues():
            level = self.vid.getLevel(neighbor_of_a.vid)
            if distance < level:
                levels.append(level)
        return levels

    def add_host_forwarding_entry(self, host):
        if self.host_forwarding_table.get(host):
            return False

        self.host_forwarding_table[host] = 0
        return True

    def __eq__(self, switch):
        return self.dpid == switch.dpid

    def __str__(self):
        return str(self.vid) + str(self.hosts)

    def __repr__(self):
        return str(self.vid) + " " + str(self.hosts)

from vid.vid import Vid


class RoutingTable(object):
    """routing table for each switch"""
    def __init__(self, dpid, vid):
        self.L = Vid.L
        self.dpid = dpid
        self.vid = vid
        self.initRT()

    def initRT(self):
        self.rtbl = {}
        vid_bin = self.vid.bin_str
        # support for local hosts
        self.rtbl[0] = {'prefix': self.vid.bin_str, 'nexthop': [1], 'gateway': []}

        for level in xrange(1, self.L + 1):
            self.rtbl[level] = {'prefix': '', 'nexthop': [], 'gateway': []}
            prefix = vid_bin[: -level] + ('1' if vid_bin[-level] == '0' else '0') + '*' * (level - 1)
            self.rtbl[level]['prefix'] = prefix

    def fillInNeighbors(self, neighbors):
        for port, neighbor in neighbors.items():
            level = self.vid.getLevel(neighbor.vid)
            if port not in self.rtbl[level]['nexthop']:
                self.rtbl[level]['nexthop'].append(port)
            if self.vid not in self.rtbl[level]['gateway']:
                self.rtbl[level]['gateway'].append(self.vid)

    def addGateway(self, level, gateway):
        if gateway not in self.rtbl[level]['gateway']:
            self.rtbl[level]['gateway'].append(gateway)

    def buildNexthops(self):
        for level in xrange(1, self.L + 1):
            for gateway in self.rtbl[level]['gateway']:
                if gateway != self.vid:
                    # find the nexthop of this gateway by looking up the table
                    for l in xrange(1, self.L + 1):
                        if gateway.match(self.rtbl[l]['prefix']):
                            for nexthop in self.rtbl[l]['nexthop']:
                                if nexthop not in self.rtbl[level]['nexthop']:
                                    self.rtbl[level]['nexthop'].append(nexthop)
                            break

    def __str__(self):
        s = '\n----> Routing Table at : {} | {} <----\n'.format(self.vid, self.dpid)
        for level in xrange(1, self.L + 1):
            s += 'level: %s, prefix: %s, nexthops: %s, gateways: %s\n' % (level, self.rtbl[level]['prefix'], self.rtbl[level]['nexthop'], self.rtbl[level]['gateway'])
        s += '--  --  --  --  -- --  --  --  --  -- --  --  --  --  -- \n'
        return s

    def __iter__(self):
        return self.rtbl

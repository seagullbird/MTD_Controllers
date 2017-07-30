class Host(object):
    """host"""
    def __init__(self, ip, mac, dpid, port):
        self.port = port
        self.dpid = dpid
        self.ip = ip
        self.local_mac = mac

    def set_switch(self, switch):
        self.switch = switch

    def set_fake_mac(self, fake_mac):
        self.fake_mac = fake_mac

    def set_sock(self, sock):
        self.sock = sock

    def update_vid(self, vid):
        self.vid = vid

    def __eq__(self, host):
        return self.local_mac == host.local_mac

    def __str__(self):
        return "Host<ip=%s, local_mac=%s, fake_mac=%s>" % (self.ip, self.local_mac, self.fake_mac)

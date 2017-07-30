def packet_out(datapath, port, pkt):
    ofproto = datapath.ofproto
    ofp = datapath.ofproto_parser
    actions = [ofp.OFPActionOutput(port)]
    buffer_id = 0xffffffff
    in_port = ofproto.OFPP_CONTROLLER
    msg = ofp.OFPPacketOut(datapath, buffer_id, in_port, actions, pkt)
    return msg
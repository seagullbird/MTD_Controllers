from . import url
import requests
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from vid.vid import Vid
import json


def post_flow(address, data):
    return requests.post(url + address, json.dumps(data))


def add_flow(data):
    address = '/stats/flowentry/add'
    return post_flow(address, data)


def mod_flow(data):
    address = '/stats/flowentry/modify'
    return post_flow(address, data)


def del_flow(data):
    address = '/stats/flowentry/delete'
    return post_flow(address, data)


def arp_request_flow_data(dpid, dst_mac):
    match = {
        'eth_type': ether_types.ETH_TYPE_ARP,
        'arp_op': arp.ARP_REQUEST
    }
    actions = [
        {
            'type': 'SET_FIELD',
            'field': 'eth_dst',
            'value': dst_mac
        },
        {
            'type': 'OUTPUT',
            'port': 'CONTROLLER',
        },
        {
            'type': 'GOTO_TABLE',
            'table_id': 2
        }
    ]
    data = {
        'priority': 65533,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return data


def add_arp_request_flow(dpid, dst_mac):
    data = arp_request_flow_data(dpid, dst_mac)
    return add_flow(data)


def mod_arp_request_flow(dpid, dst_mac):
    data = arp_request_flow_data(dpid, dst_mac)
    return mod_flow(data)


def arp_dir_transfer_data(dpid, dst_mac):
    match = {
        'eth_dst': dst_mac
    }
    actions = [
        {
            'type': 'GOTO_TABLE',
            'table_id': 2
        }
    ]
    data = {
        'priority': 65534,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return data


def add_arp_dir_transfer_flow(dpid, dst_mac):
    data = arp_dir_transfer_data(dpid, dst_mac)
    return add_flow(data)


def del_arp_dir_transfer_flow(dpid, dst_mac):
    data = arp_dir_transfer_data(dpid, dst_mac)
    return del_flow(data)


def add_lldp_disable_flow(dpid):
    match = {
        'eth_type': ether_types.ETH_TYPE_LLDP
    }
    actions = []
    data = {
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return mod_flow(data)


def add_host_packet_modify_flow(dpid):
    match = {
        'eth_dst': '00:00:00:00:00:00/ff:ff:ff:ff:00:00'
    }
    actions = [
        {
            'type': 'GOTO_TABLE',
            'table_id': 1
        }
    ]
    data = {
        'priority': 65532,
        'table_id': 0,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return add_flow(data)


def add_resubmit_flow(dpid, table_id, goto_id):
    actions = [
        {
            'type': 'GOTO_TABLE',
            'table_id': goto_id
        }
    ]
    data = {
        'table_id': table_id,
        'dpid': dpid,
        'actions': actions
    }
    return add_flow(data)


def add_routing_table_flow(dpid, prefix, port):
    match = {
        'eth_dst': Vid.prefix2mac(prefix)
    }
    actions = [
        {
            'type': 'OUTPUT',
            'port': port
        }
    ]
    data = {
        'priority': 65534,
        'table_id': 2,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return add_flow(data)


def add_goto_table3_flow(dpid, vid):
    match = {
        'eth_dst': Vid.vid2mac(vid.sw, vid.host) + "/ff:ff:ff:ff:00:00"
    }
    actions = [
        {
            'type': 'GOTO_TABLE',
            'table_id': 3
        }
    ]
    data = {
        'table_id': 2,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return add_flow(data)


def host_forwarding_flow_data(dpid, host_vid, switch_vid):
    match = {
        'eth_dst': Vid.vid2mac(host_vid.sw, host_vid.host)
    }
    actions = [
        {
            'type': 'SET_FIELD',
            'field': 'eth_dst',
            'value': Vid.vid2mac(switch_vid.sw, host_vid.host)
        },
        {
            'type': 'GOTO_TABLE',
            'table_id': 2
        }
    ]
    data = {
        'priority': 65535,
        'table_id': 1,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return data

def add_host_forwarding_flow(dpid, host_vid, switch_vid):
    data = host_forwarding_flow_data(dpid, host_vid, switch_vid)
    return add_flow(data)


def del_host_forwarding_flow(dpid, host_vid, switch_vid):
    data = host_forwarding_flow_data(dpid, host_vid, switch_vid)
    return del_flow(data)


def host_receiving_flow_data(dpid, vid, port):
    match = {
        'eth_dst': Vid.vid2mac(vid.sw, vid.host) + "/00:00:00:00:ff:ff"
    }
    actions = [
        {
            'type': 'OUTPUT',
            'port': port
        }
    ]
    data = {
        'priority': 65535,
        'table_id': 3,
        'dpid': dpid,
        'match': match,
        'actions': actions
    }
    return data


def add_host_receiving_flow(dpid, vid, port):
    data = host_receiving_flow_data(dpid, vid, port)
    return add_flow(data)


def del_host_receiving_flow(dpid, vid, port):
    data = host_receiving_flow_data(dpid, vid, port)
    return del_flow(data)


def clear_routing_table(dpid, table_id):
    data = {
        'dpid': dpid,
        'table_id': table_id
    }
    return del_flow(data)
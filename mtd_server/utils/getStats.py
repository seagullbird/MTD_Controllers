import requests
import json
from . import url
from topo.host import Host


def get_stats(address):
    return json.loads(requests.get(url + address).text)


def get_topo_links():
    address = '/v1.0/topology/links'
    links = get_stats(address)
    return [(int(link['src']['dpid'], 16), int(link['dst']['dpid'], 16), int(link['src']['port_no'])) for link in links]


def get_dpids():
    address = '/stats/switches'
    return get_stats(address)


def get_hosts():
    address = '/v1.0/topology/hosts'
    return get_stats(address)


def get_host(mac_addr):
    hosts = get_hosts()
    for host in hosts:
        if host['mac'] == mac_addr:
            return Host(str(host['ipv4'][0]), str(host['mac']), int(host['port']['dpid'], 16), int(host['port']['port_no']))
    return
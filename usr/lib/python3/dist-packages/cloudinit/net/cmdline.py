#   Copyright (C) 2013-2014 Canonical Ltd.
#
#   Author: Scott Moser <scott.moser@canonical.com>
#   Author: Blake Rouse <blake.rouse@canonical.com>
#
#   Curtin is free software: you can redistribute it and/or modify it under
#   the terms of the GNU Affero General Public License as published by the
#   Free Software Foundation, either version 3 of the License, or (at your
#   option) any later version.
#
#   Curtin is distributed in the hope that it will be useful, but WITHOUT ANY
#   WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
#   more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with Curtin.  If not, see <http://www.gnu.org/licenses/>.

import base64
import glob
import gzip
import io
import shlex
import sys

import six

from . import get_devicelist
from . import sys_netdev_info

from cloudinit import util

PY26 = sys.version_info[0:2] == (2, 6)


def _shlex_split(blob):
    if PY26 and isinstance(blob, six.text_type):
        # Older versions don't support unicode input
        blob = blob.encode("utf8")
    return shlex.split(blob)


def _load_shell_content(content, add_empty=False, empty_val=None):
    """Given shell like syntax (key=value\nkey2=value2\n) in content
       return the data in dictionary form.  If 'add_empty' is True
       then add entries in to the returned dictionary for 'VAR='
       variables.  Set their value to empty_val."""
    data = {}
    for line in _shlex_split(content):
        key, value = line.split("=", 1)
        if not value:
            value = empty_val
        if add_empty or value:
            data[key] = value

    return data


def _klibc_to_config_entry(content, mac_addrs=None):
    """Convert a klibc writtent shell content file to a 'config' entry
    When ip= is seen on the kernel command line in debian initramfs
    and networking is brought up, ipconfig will populate
    /run/net-<name>.cfg.

    The files are shell style syntax, and examples are in the tests
    provided here.  There is no good documentation on this unfortunately.

    DEVICE=<name> is expected/required and PROTO should indicate if
    this is 'static' or 'dhcp'.
    """

    if mac_addrs is None:
        mac_addrs = {}

    data = _load_shell_content(content)
    try:
        name = data['DEVICE']
    except KeyError:
        raise ValueError("no 'DEVICE' entry in data")

    # ipconfig on precise does not write PROTO
    proto = data.get('PROTO')
    if not proto:
        if data.get('filename'):
            proto = 'dhcp'
        else:
            proto = 'static'

    if proto not in ('static', 'dhcp', 'dhcp6'):
        raise ValueError("Unexpected value for PROTO: %s" % proto)

    iface = {
        'type': 'physical',
        'name': name,
        'subnets': [],
    }

    if name in mac_addrs:
        iface['mac_address'] = mac_addrs[name]

    # Handle both IPv4 and IPv6 values
    for v, pre in (('ipv4', 'IPV4'), ('ipv6', 'IPV6')):
        # if no IPV4ADDR or IPV6ADDR, then go on.
        if pre + "ADDR" not in data:
            continue
        if pre + "PROTO" in data:
            subnet = {'type': data[pre + 'PROTO'], 'control': 'manual'}
        else:
            subnet = {'type': proto, 'control': 'manual'}

        # these fields go right on the subnet
        for key in ('NETMASK', 'BROADCAST', 'GATEWAY'):
            if pre + key in data:
                subnet[key.lower()] = data[pre + key]

        dns = []
        # handle IPV4DNS0 or IPV6DNS0
        for nskey in ('DNS0', 'DNS1'):
            ns = data.get(pre + nskey)
            # verify it has something other than 0.0.0.0 (or ipv6)
            if ns and len(ns.strip(":.0")):
                dns.append(data[pre + nskey])
        if dns:
            subnet['dns_nameservers'] = dns
            # add search to both ipv4 and ipv6, as it has no namespace
            search = data.get('DOMAINSEARCH')
            if search:
                if ',' in search:
                    subnet['dns_search'] = search.split(",")
                else:
                    subnet['dns_search'] = search.split()

        iface['subnets'].append(subnet)

    return name, iface


def config_from_klibc_net_cfg(files=None, mac_addrs=None):
    if files is None:
        files = glob.glob('/run/net*.conf')

    entries = []
    names = {}
    for cfg_file in files:
        name, entry = _klibc_to_config_entry(util.load_file(cfg_file),
                                             mac_addrs=mac_addrs)
        if name in names:
            raise ValueError(
                "device '%s' defined multiple times: %s and %s" % (
                    name, names[name], cfg_file))

        names[name] = cfg_file
        entries.append(entry)
    return {'config': entries, 'version': 1}


def _decomp_gzip(blob, strict=True):
    # decompress blob. raise exception if not compressed unless strict=False.
    with io.BytesIO(blob) as iobuf:
        gzfp = None
        try:
            gzfp = gzip.GzipFile(mode="rb", fileobj=iobuf)
            return gzfp.read()
        except IOError:
            if strict:
                raise
            return blob
        finally:
            if gzfp:
                gzfp.close()


def _b64dgz(b64str, gzipped="try"):
    # decode a base64 string.  If gzipped is true, transparently uncompresss
    # if gzipped is 'try', then try gunzip, returning the original on fail.
    try:
        blob = base64.b64decode(b64str)
    except TypeError:
        raise ValueError("Invalid base64 text: %s" % b64str)

    if not gzipped:
        return blob

    return _decomp_gzip(blob, strict=gzipped != "try")


def read_kernel_cmdline_config(files=None, mac_addrs=None, cmdline=None):
    if cmdline is None:
        cmdline = util.get_cmdline()

    if 'network-config=' in cmdline:
        data64 = None
        for tok in cmdline.split():
            if tok.startswith("network-config="):
                data64 = tok.split("=", 1)[1]
        if data64:
            return util.load_yaml(_b64dgz(data64))

    if 'ip=' not in cmdline:
        return None

    if mac_addrs is None:
        mac_addrs = dict((k, sys_netdev_info(k, 'address'))
                         for k in get_devicelist())

    return config_from_klibc_net_cfg(files=files, mac_addrs=mac_addrs)

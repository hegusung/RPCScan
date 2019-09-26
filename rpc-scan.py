#!/usr/bin/python3
# -*- coding: utf-8 -
import sys
import struct
import time
from ipaddress import IPv4Network
from operator import itemgetter
from os.path import join
import argparse

from lib.portmap import Portmap
from lib.mount import Mount, MountAccessError
from lib.nfs import NFS, NFSAccessError
from lib.utils import *

#
# Author: Hegusung
#

def showmount(host, port, timeout):
    portmap = Portmap(host, port, timeout)
    portmap.connect()
    port = portmap.getport(Mount.program, Mount.program_version)

    mount = Mount(host, port, timeout)
    mount.connect()
    exports = mount.export()

    mount.disconnect()
    portmap.disconnect()

    return exports

def listnfs(host, port, timeout, recurse=1, uid=0, gid=0, auth_hostname='nfsclient'):
    portmap = Portmap(host, port, timeout)
    portmap.connect()

    mount_port = portmap.getport(Mount.program, Mount.program_version)
    mount = Mount(host, mount_port, timeout)
    mount.connect()

    exports = mount.export()

    auth = {
        "flavor": 1, #AUTH_UNIX
        "machine_name": auth_hostname,
        "uid": uid,
        "gid": gid,
        "aux_gid": [gid],
    }

    nfs_port = portmap.getport(NFS.program, NFS.program_version)
    nfs = NFS(host, nfs_port, timeout)
    nfs.connect()

    contents = []

    for export in exports:
        try:
            mount_info = mount.mnt(export["path"], auth=auth)

            contents += listdir(nfs, auth, mount_info["file_handle"], "nfs://%s:%d%s" % (host, nfs_port, export["path"]), recurse=recurse)

        except MountAccessError:
            pass


    portmap.disconnect()
    mount.disconnect()
    nfs.disconnect()

    return contents

def listdir(nfs, auth, file_handle, path, recurse=1):
    if recurse == 0:
        return [path + "/"]

    try:
        items = nfs.readdirplus(file_handle, auth=auth)
    except NFSAccessError:
        return []

    if len(items) == 0:
        return [path + "/"]

    contents = []

    for item in items:
        if item["name"] in [".", ".."]:
            continue

        if item["file_type"] == 2:
            try:
                contents += listdir(nfs, auth, item["file_handle"], join(path, item["name"]), recurse=recurse-1)
            except NFSAccessError:
                contents.append(join(path, item["name"]) + "/")

        else:
            contents.append(join(path, item["name"]))

    return contents

def process(host, port, timeout, actions, uid, gid, auth_hostname, recurse):
    try:
        portmap = Portmap(host, 111, timeout)
        portmap.connect()
        res = portmap.null()
        portmap.disconnect()

        rpc_names = parse_rpc_names('rpc_names.csv')

        if res:
            print("rpc://%s:%d\tPortmapper" % (host, port))

            if "list_rpc" in actions:
                print("RPC services for %s:" % host)
                portmap.connect()
                for item in sorted(portmap.dump(),key=itemgetter('program')):
                    name = str(item["program"])
                    for rpc_service in rpc_names:
                        if item["program"] in rpc_service["range"]:
                            name = "%s (%d)" % (rpc_service["name"], item["program"])
                            break
                    print("%s %s %s %s" % (name.ljust(30), str(item["version"]).ljust(10), item["protocol"].ljust(10), str(item["port"]).ljust(10)))
                portmap.disconnect()

            if "list_mounts" in actions:
                print("Exports for %s:" % host)
                for item in showmount(host, port, timeout):
                    print("%s %s" % (item["path"].ljust(20), ','.join(item["authorized"])))

            if "list_nfs" in actions:
                for item in listnfs(host, port, timeout, recurse=recurse, uid=uid, gid=gid, auth_hostname=auth_hostname):
                    print(item)

    except OSError:
        pass
    except Exception as e:
        raise e
        print("%s:%d Exception %s:%s" % (host, port, type(e), e))

def main():
    parser = argparse.ArgumentParser(description='Tool to perform rpc recon on hosts', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('ip_range', help='ip or ip range', nargs='?', default=None)
    parser.add_argument('-H', help='Host:port file', dest='host_file', default=None)
    parser.add_argument('-p', help='port', dest='port', default=111, type=int)
    parser.add_argument('-t', help='timeout', nargs='?', default=15, type=int, dest='timeout')
    parser.add_argument('--rpc', help='list rpc (portmapper)', action='store_true', dest='list_rpc')
    parser.add_argument('--mounts', help='list mounts', action='store_true', dest='list_mounts')
    parser.add_argument('--nfs', help='list nfs', action='store_true', dest='list_nfs')
    parser.add_argument('-u', help='uid', nargs='?', default=0, type=int, dest='uid')
    parser.add_argument('-g', help='gid', nargs='?', default=0, type=int, dest='gid')
    parser.add_argument('--hostname', help='authentication hostname', nargs='?', default="nfsclient", type=str, dest='hostname')
    parser.add_argument('--recurse', help='recurse levels', nargs='?', default=1, type=int, dest='recurse')


    args = parser.parse_args()

    if args.ip_range == None and args.host_file == None:
        parser.print_help()
        sys.exit()

    port = args.port

    timeout = args.timeout
    actions = []
    if args.list_rpc:
        actions.append("list_rpc")
    if args.list_mounts:
        actions.append("list_mounts")
    if args.list_nfs:
        actions.append("list_nfs")

    if args.ip_range != None:
        for ip in IPv4Network(args.ip_range):
            process(str(ip), port, timeout, actions, args.uid, args.gid, args.hostname, args.recurse)

    if args.host_file != None:
        with open(args.host_file) as f:
            for line in f:
                host_port = line.split()[0]
                if ":" in host_port:
                    process(host_port.split(":")[0], int(host_port.split(":")[1]), timeout, actions, args.uid, args.gid, args.hostname, args.recurse)
                else:
                    process(host_port, port, timeout, actions, args.uid, args.gid, args.hostname, args.recurse)




if __name__ == '__main__':
    main()

#!/usr/bin/env python
# coding: utf-8
import time
import argparse
from urllib.parse import urlparse

from lib.portmap import Portmap
from lib.mount import Mount
from lib.nfs import NFS

#
# Author: Hegusung
#

def main():
    parser = argparse.ArgumentParser(description='download a nfs file', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('nfs_path', help='nfs path', nargs='?', default=None)
    parser.add_argument('-t', help='timeout', nargs='?', default=15, type=int, dest='timeout')
    parser.add_argument('-u', help='uid', nargs='?', default=0, type=int, dest='uid')
    parser.add_argument('-g', help='gid', nargs='?', default=0, type=int, dest='gid')
    parser.add_argument('--hostname', help='authentication hostname', nargs='?', default="nfsclient", type=str, dest='hostname')
    parser.add_argument('-d', help='destination file', nargs='?', type=str, dest='destination_file')

    args = parser.parse_args()
    nfs_path = args.nfs_path
    timeout = args.timeout

    auth = {
        "flavor": 1, #AUTH_UNIX
        "machine_name": args.hostname,
        "uid": args.uid,
        "gid": args.gid,
        "aux_gid": [args.gid],
    }

    if not nfs_path.startswith("nfs://"):
        raise Exception("nfs path should start with nfs://")

    o = urlparse(nfs_path)

    host = o.netloc
    uri = o.path

    portmapper_port = 111
    portmap = Portmap(host, portmapper_port, timeout)
    portmap.connect()

    # get mount service port
    mount_port = portmap.getport(Mount.program, Mount.program_version)
    mount = Mount(host, mount_port, timeout)
    mount.connect()

    # list mount points and grab the correct file handle
    file_handle = None
    for mountpoint in mount.export():
        if uri.startswith(mountpoint["path"]):
            mount_path = mountpoint["path"]
            file_handle = mount.mnt(mountpoint["path"])["file_handle"]
            file_type = 2

    if file_handle == None:
        mount.disconnect()
        portmap.disconnect()
        raise Exception("Mount point not found")

    # get nfs port
    nfs_port = portmap.getport(NFS.program, NFS.program_version)
    nfs = NFS(host, nfs_port, timeout)
    nfs.connect()

    # iterate through folders
    folders_str = uri[len(mount_path):]

    for folder in folders_str.split("/"):
        if len(folder) == 0:
            continue

        res = nfs.lookup(file_handle, folder, auth=auth)
        if res["file_type"] == 2: # DIR
            file_handle = res["file_handle"]
            file_type = res["file_type"]
        elif res["file_type"] in [1] and folder == folders_str.split("/")[-1]: # last file
            file_handle = res["file_handle"]
            file_type = res["file_type"]
        else:
            raise Exception("Unexpected file type")

    # We got the handle, read file
    if file_type == 1: # regular file
        data = nfs.read(file_handle, auth=auth)
        if args.destination_file == None:
            file_name = folders_str.split("/")[-1]
        else:
            file_name = args.destination_file
        f = open(file_name, 'wb')
        f.write(data)
        f.close()
        print("file %s written" % file_name)
    else:
        raise Exception("Unexpected file type")

if __name__ == '__main__':
    main()

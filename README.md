# RPCScan
Tool to communicate with RPC services and check misconfigurations on NFS shares

This tool currently has the following features:
* Listing RPC services using portmap 
* Listing mountpoints on hosts using mount service
* Perform recursive listing on NFS share
* List a directory accessible via NFS
* Download a file accessible via NFS

## RPCScan Usage

If the 'insecure' paramater is not set on the NFS server configuration, it will be necessary to run the script as root because the NFS server will check whether the incomming communication comes from a source port <= 1024 when connecting with uid=0 (root).

### rpc-scan.py

#### Listing RPC services
```
rpc-scan.py <host/host_range> --rpc
```

#### Listing mountpoints
```
rpc-scan.py <host/host_range> --mounts
```

#### Recursing listing of NFS shares
```
rpc-scan.py <host/host_range> --nfs --recurse 3
```

### nfs-ls.py
```
nfs-ls.py nfs://<host>/directory/path
```

### nfs-get.py
```
nfs-get.py nfs://<host>/file/path.txt -d output_name.txt
```

#### Dependencies

- python3
- argparse

#### Misc

The rpc_names.csv file is taken from the IANA website:
https://www.iana.org/assignments/rpc-program-numbers/rpc-program-numbers.xhtml

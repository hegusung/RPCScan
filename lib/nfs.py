import struct

from .rpc import RPC

#
# Author: Hegusung
#

# NFS: 100003
# Procedures:
# - NULL: 0
# - GETATTR: 1
# - LOOKUP: 3
# - ACCESS: 4
# - READLINK: 5
# - READ: 6
# - READDIRPLUS: 17

class NFSAccessError(Exception):
    pass

class NFS(RPC):
    program = 100003
    program_version = 3

    def null(self):
        procedure = 0 # Null

        super(NFS, self).request(self.program, self.program_version, procedure)

        # no exception raised
        return True

    def lookup(self, dir_handle, file_folder, auth=None):
        if type(dir_handle) != bytes:
            raise Exception("file_id should be bytes")

        procedure = 3 # Lookup

        data = struct.pack('!L', len(dir_handle))
        data += dir_handle
        data += b'\x00'*((4-len(dir_handle) % 4)%4)

        data += struct.pack('!L', len(file_folder))
        data += file_folder.encode()
        data += b'\x00'*((4-len(file_folder) % 4)%4)

        data = super(NFS, self).request(self.program, self.program_version, procedure, data=data, auth=auth)

        nfs_status = struct.unpack('!L', data[:4])[0]
        data = data[4:]

        if nfs_status != 0:
            raise NFSAccessError("Error: %d" % nfs_status)

        file_handle_len = struct.unpack("!L", data[:4])[0]
        data = data[4:]

        file_handle = data[:file_handle_len]
        data = data[file_handle_len:]
        data = data[(4-file_handle_len % 4)%4:]

        value_follows = data[:4]
        data = data[4:]

        if value_follows == b'\x00\x00\x00\x01':
            attributes = data[:84]
            data = data[84:]

            (file_type, mode, ulink, uid, gid, file_size) = struct.unpack('!LLLLLL', attributes[:24])
            # File types:
            # 1: Regular file
            # 2: Directory
            # 5: Symbolic link
        else:
            file_type = None
            file_size = None

        return {
            "file_handle": file_handle,
            "file_type": file_type,
            "file_size": file_size,
        }

    def read(self, file_handle, auth=None, offset=0, chunk_count=1024*1024):
        if type(file_handle) != bytes:
            raise Exception("file_id should be bytes")

        procedure = 6 # Read

        data = struct.pack('!L', len(file_handle))
        data += file_handle
        data += b'\x00'*((4-len(file_handle) % 4)%4)
        data += struct.pack('!QL', offset, chunk_count)

        data = super(NFS, self).request(self.program, self.program_version, procedure, data=data, auth=auth)

        nfs_status = struct.unpack('!L', data[:4])[0]
        data = data[4:]

        if nfs_status != 0:
            raise NFSAccessError("Error: %d" % nfs_status)

        value_follows = data[:4]
        data = data[4:]

        if value_follows == b'\x00\x00\x00\x01':
            attributes = data[:84]
            data = data[84:]

            (file_type, mode, ulink, uid, gid, file_size) = struct.unpack('!LLLLLL', attributes[:24])
            # File types:
            # 1: Regular file
            # 2: Directory
            # 5: Symbolic link
        else:
            file_type = None
            file_size = None

        (count, EOF) = struct.unpack('!LL', data[:8])
        data = data[8:]

        file_len = struct.unpack("!L", data[:4])[0]
        data = data[4:]
        file_data = data[:file_len]
        data = data[file_len:]
        data = data[(4-file_len % 4)%4:]

        if len(file_data) != count:
            raise Exception("File size mismatch")

        if EOF == 0:
            file_data += self.read(file_handle, auth=auth, offset=offset+len(file_data))

        return file_data

    def readdirplus(self, dir_handle, cookie=0, auth=None):
        # file_id should by bytes
        if type(dir_handle) != bytes:
            raise Exception("file_id should be bytes")

        procedure = 17 # Export

        dircount = 4096
        maxcount = dircount*8

        data = struct.pack('!L', len(dir_handle))
        data += dir_handle
        data += struct.pack('!Q', cookie)
        data += struct.pack('!QLL', 0, dircount, maxcount)

        data = super(NFS, self).request(self.program, self.program_version, procedure, data=data, auth=auth)

        nfs_status = struct.unpack('!L', data[:4])[0]
        data = data[4:]

        if nfs_status != 0:
            raise NFSAccessError("Error: %d" % nfs_status)

        dir_attributes = data[:88]
        data = data[88:]

        opaque_data = data[:8]
        data = data[8:]

        contents = []
        last_cookie = 0

        value_follows = data[:4]
        data = data[4:]
        while value_follows == b'\x00\x00\x00\x01':
            file_id = struct.unpack("!Q", data[:8])[0]
            data = data[8:]

            name_len = struct.unpack("!L", data[:4])[0]
            data = data[4:]

            name = data[:name_len].decode()
            data = data[name_len:]
            data = data[(4-name_len % 4)%4:]

            cookie = struct.unpack("!Q", data[:8])[0]
            last_cookie = cookie
            data = data[8:]

            value_follows = data[:4]
            data = data[4:]

            if value_follows == b'\x00\x00\x00\x01':
                attributes = data[:84]
                data = data[84:]

                (file_type, mode, ulink, uid, gid, file_size) = struct.unpack('!LLLLLL', attributes[:24])
                # File types:
                # 1: Regular file
                # 2: Directory
                # 5: Symbolic link
            else:
                file_type = None
                file_size = None

            handle_value_follows = data[:4]
            data = data[4:]

            if handle_value_follows == b'\x00\x00\x00\x01':
                len_file_handle = struct.unpack('!L', data[:4])[0]
                data = data[4:]
                file_handle = data[:len_file_handle]
                data = data[len_file_handle:]
            else:
                file_handle = None

            contents.append({
                "name": name,
                "file_type": file_type,
                "cookie": cookie,
                "file_id": file_id,
                "file_handle": file_handle,
                "file_size": file_size,
            })

            value_follows = data[:4]
            data = data[4:]

        EOF = data[:4]

        if EOF == b'\x00\x00\x00\x00':
            self.readdirplus(dir_handle, cookie=last_cookie, auth=auth)

        return contents



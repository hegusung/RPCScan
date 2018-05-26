import struct

from .rpc import RPC

#
# Author: Hegusung
# 

class MountAccessError(Exception):
    pass

class Mount(RPC):
    program = 100005
    program_version = 3

    def null(self, auth=None):
        procedure = 0 # Null

        super(Mount, self).request(self.program, self.program_version, procedure, auth=auth)

        # no exception raised
        return True

    def mnt(self, path, auth=None):
        procedure = 1

        data = struct.pack('!L', len(path))
        data += path.encode()
        data += b'\x00'*((4-len(path) % 4)%4)

        data = super(Mount, self).request(self.program, self.program_version, procedure, data=data, auth=auth)

        status = struct.unpack('!L', data[:4])[0]
        data = data[4:]

        if status != 0:
            raise MountAccessError("MNT error: %d" % status)

        len_file_handle = struct.unpack('!L', data[:4])[0]
        data = data[4:]
        file_handle = data[:len_file_handle]
        data = data[len_file_handle:]

        flavors = []
        flavors_nb = struct.unpack('!L', data[:4])[0]
        data = data[4:]
        for _ in range(flavors_nb):
            flavor = struct.unpack('!L', data[:4])[0]
            flavors.append(flavor)
            data = data[4:]

        return {
            "file_handle": file_handle,
            "flavors": flavors,
        }


    def export(self):
        # RPC
        procedure = 5 # Export

        export = super(Mount, self).request(self.program, self.program_version, procedure)

        exports = []

        export_Value_Follows = export[:4]
        export_Entries = export[4:]

        while export_Value_Follows == b'\x00\x00\x00\x01':
            (path_len,) = struct.unpack('!L', export_Entries[:4])
            export_Entries = export_Entries[4:]

            path = export_Entries[:path_len].decode('utf-8')

            export_Entries = export_Entries[path_len:]

            export_Entries = export_Entries[(4-path_len % 4)%4:]

            group_value_follows = export_Entries[:4]
            export_Entries = export_Entries[4:]

            authorized_ip = []

            while group_value_follows == b'\x00\x00\x00\x01':
                (ip_len,) = struct.unpack('!L', export_Entries[:4])
                export_Entries = export_Entries[4:]

                ip = export_Entries[:ip_len].decode('utf-8')
                authorized_ip.append(ip)

                export_Entries = export_Entries[ip_len:]

                export_Entries = export_Entries[(4-ip_len % 4)%4:]

                group_value_follows = export_Entries[:4]
                export_Entries = export_Entries[4:]

            exports.append({
                "path": path,
                "authorized": authorized_ip,
            })

            export_Value_Follows = export_Entries[:4]
            export_Entries = export_Entries[4:]


        return exports



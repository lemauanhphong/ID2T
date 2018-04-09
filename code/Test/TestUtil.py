#!/usr/bin/python3

import scapy.main

# This import is needed, otherwise scapy throws warnings. When reading a pcap scapy will not
# find the layer-type 1 (ethernet) because it has not been loaded at the time. To circumvent
# this we explicitely load the ethernet-type here.
# For the curious guys and gals, the exact error message is:
# "RawPcapReader: unknown LL type [%i]/[%#x]. Using Raw packets" % the_missing_ll_number
# If the same problems happens with other ll-types feel free to load ALL imaginable layers
# with the following line.
# import scapy.layers.all
import scapy.layers.l2

import scapy.packet
import scapy.utils
import shlex
import subprocess
import os


# You could compare pcaps by byte or by hash too, but this class tells you
# where exactly pcaps differ
class PcapComparator:
    def compare_files(self, file: str, other_file: str):
        self.compare_captures(scapy.utils.rdpcap(file), scapy.utils.rdpcap(other_file))

    def compare_captures(self, packetsA, packetsB):
        if len(packetsA) != len(packetsB):
            self.fail("Both pcaps have to have the same amount of packets")

        for i in range(len(packetsA)):
            p, p2 = packetsA[i], packetsB[i]

            if abs(p.time - p2.time) > (10 ** -7):
                self.fail("Packets no %i in the pcaps don't appear at the same time" % (i + 1))
            self.compare_packets(p, p2, i + 1)

    def compare_packets(self, p: scapy.packet.BasePacket, p2: scapy.packet.BasePacket, packet_number: int):
        if p == p2:
            return

        while type(p) != scapy.packet.NoPayload or type(p2) != scapy.packet.NoPayload:
            if type(p) != type(p2):
                self.fail("Packets %i are of incompatible types: %s and %s" % (packet_number, type(p).__name__, type(p2).__name__))

            for field in p.fields:
                if p.fields[field] != p2.fields[field]:
                    packet_type = type(p).__name__
                    v, v2 = p.fields[field], p2.fields[field]

                    self.fail("Packets %i differ in field %s.%s: %s != %s" %
                                (packet_number, packet_type, field, v, v2))

            p = p.payload
            p2 = p2.payload

    def fail(self, message: str):
        raise AssertionError(message)


class ID2TExecution:
    ID2T_PATH = ".."
    ID2T_LOCATION = ID2T_PATH + "/" + "id2t"

    OUTPUT_FILES_PREFIX_LINE = "Output files created:"

    def __init__(self, input_filename, id2t_path=ID2T_LOCATION, seed=None):
        self.input_file = input_filename
        self.seed = str(seed)
        self.id2t_path = id2t_path

        self.generated_files = [] # files generated by id2t
        self.keep_files = []
        self.return_code = None
        self.id2t_output = None

    def has_run(self):
        return self.return_code is not None

    def run(self, parameters):
        if self.has_run():
            raise RuntimeError("This instance has already run and can't do it again")

        command = self.get_run_command(parameters)
        return_code, output = subprocess.getstatusoutput(command)
        self.return_code = return_code
        self.id2t_output = output

        self.generated_files = self._parse_files(output)

    def get_run_command(self, parameters):
        command_args = [self.id2t_path, "-i", self.input_file]
        if self.seed is not None:
            command_args.extend(["-S", self.seed])
        command_args.extend(["-a", "MembersMgmtCommAttack"])
        command_args.extend(parameters)

        return " ".join(map(shlex.quote, command_args))

    def _parse_files(self, program_output: str) -> "list[str]":
        lines = program_output.split(os.linesep)

        if self.OUTPUT_FILES_PREFIX_LINE not in lines:
            raise AssertionError("The magic string is not in the program output anymore, has the program output structure changed?")
        index = lines.index(self.OUTPUT_FILES_PREFIX_LINE)
        next_empty_line_index = lines.index("", index) if "" in lines[index:] else len(lines)

        return lines[index + 1:next_empty_line_index]

    def get_pcap_filename(self):
        self._require_run()
        return self._find_pcap()

    def get_output(self):
        self._require_run()
        return self.id2t_output

    def get_return_code(self):
        self._require_run()
        return self.return_code

    def keep_file(self, file):
        self._require_run()

        if file not in self.generated_files:
            raise ValueError("%s is not generated by id2t" % file)
        if file not in self.keep_files:
            self.keep_files.append(file)

    def get_kept_files(self):
        self._require_run()
        return self.keep_files

    def get_generated_files(self):
        self._require_run()
        return self.generated_files

    def get_files_for_deletion(self):
        self._require_run()
        return [file for file in self.generated_files if file not in self.keep_files and not "No packets were injected." in file]

    def _find_pcap(self) -> str:
        for gen_file in self.generated_files:
            if "No packets were injected." in gen_file:
                return "No packets were injected."

        return next(file for file in self.generated_files if file.endswith(".pcap"))

    def _require_run(self):
        if not self.has_run():
            raise RuntimeError("You have to execute run() before you can call this method")

    def cleanup(self):
        if self.has_run():
            id2t_relative = os.path.dirname(self.id2t_path)

            for file in self.get_files_for_deletion():
                if "No packets were injected." in file:
                    pass

                try:
                    os.unlink(id2t_relative + "/" + file)
                except: pass

    def __del__(self):
        self.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: %s one.pcap other.pcap" % sys.argv[0])
        exit(0)

    try:
        PcapComparator().compare_files(sys.argv[1], sys.argv[2])
        print("The given pcaps are equal")
    except AssertionError as e:
        print("The given pcaps are not equal")
        print("Error message:", *e.args)
        exit(1)
    except Exception as e:
        print("During the comparison an unexpected error happened")
        print(type(e).__name__ + ":", *e.args)
        exit(1)

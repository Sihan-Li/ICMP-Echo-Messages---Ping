import struct
import sys
import socket
import threading
import os
import time

class Ping(object):
    def __init__(self,hostname,number_of_pings,request_period,timeout):
        self.number_of_pings = number_of_pings
        self.target = hostname
        self.timeout = timeout / 1000
        self.received_requests = 0
        self.min_rtt = 0
        self.max_rtt = 0
        self.total_rtt = 0
        self.counter = 0

    def create_checksum(self, data):
        if len(data) % 2 != 0:
            data += b'\x00'
        res = 0
        for i in range(0, len(data), 2):
            fst = res
            snd = (data[i] << 8) + data[i + 1]
            res = fst + snd
            if res < 65536:
                res = res
            else:
                res = res + 1 - 65536
        return ~res & 0xffff

    def create_request(self,seqno):
        identifier = os.getpid()
        timestamp = int(time.time())*1000*1000
        tempCheckSum = struct.pack('!bbHHHQ', 8, 0,0, identifier, seqno, timestamp)
        checksum = self.create_checksum(tempCheckSum)
        request = struct.pack('!bbHHHQ', 8, 0, checksum, identifier, seqno, timestamp)
        return request


    def send_request(self,seqno,target,sock):
        request = self.create_request(seqno)
        sock.sendto(request,(target,1))


    def receive_reply(self,sendTime,sock):
        endpoint = sendTime + self.timeout
        while True:
            sock.settimeout(endpoint - time.time())
            try:
                packet, addr = sock.recvfrom(1024)
                return [packet,addr]
            except:
                return

    def handleSingleTask(self,seqno,target):
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        #we send , and then receive
        self.send_request(seqno,target,sock)
        sendTime = time.time()
        #extract the pack and address from it
        res = self.receive_reply(sendTime,sock)
        if res:
            packet = res[0]
            addr = res[1]

            header = packet[20:36]
            TTL = packet[8:9]
            ttl = struct.unpack('!B', TTL)[0]
            ipAddress = addr[0]

            totalRTTTime = time.time() - sendTime
            self.total_rtt += totalRTTTime

            newtype, newcode, newchecksum, newidentifier, newseq, newtimestamp = struct.unpack('!bbHHHQ', header)
            sock.close()

        else:
            return

        #the sequence number we receive is not the one we send
        if newseq != seqno:
            return

        #check whether the checksum is vaild
        if self.create_checksum(header) == 0:
            self.received_requests += 1
            self.min_rtt = min(self.min_rtt, totalRTTTime)
            self.max_rtt = max(self.max_rtt, totalRTTTime)
            print("{} bytes from {}: icmp_seq={} ttl={} time={} ms".format(len(packet),ipAddress,seqno,int(ttl),totalRTTTime*1000))
        else:
            print("Invalid chacksum")



if __name__ == '__main__':
    server_hostname = sys.argv[1]
    number_of_pings = int(sys.argv[2])
    request_period = float(sys.argv[3])
    socket_timeout = float(sys.argv[4])
    flag = []

    p = Ping(server_hostname,number_of_pings,request_period,socket_timeout)

    start_time = time.time()

    threads = []
    for i in range(number_of_pings):
        t = threading.Timer(request_period//1000 * i, p.handleSingleTask,(i+1,server_hostname,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    all_runnint_time = time.time() - start_time
    percentage = round(((number_of_pings - p.received_requests) / number_of_pings) * 100, 2)
    avg_rtt = round(p.total_rtt / p.received_requests, 2)
    print('--- ' + p.target + " ping statistics ---")
    print("{} packets transmitted, {} received, {}% packet loss, time {}ms".format(number_of_pings,p.received_requests,percentage,all_runnint_time*1000))
    print("rtt min/avg/max = {}/{}/{} ms".format(p.min_rtt*1000, avg_rtt*1000, p.max_rtt*1000))




       # nowTime = time
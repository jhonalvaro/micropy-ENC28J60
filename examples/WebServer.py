#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2023 Przemyslaw Bereski https://github.com/przemobe/

from machine import Pin, SPI
import Ntw
import Dhcp4Client
import time

class WebServer:
    def __init__(self, ntw):
        self.ntw = ntw
        self.ntw.registerTcp4Callback(80, self.handle_request)

    def handle_request(self, pkt):
        if pkt.tcp_flags & 0x0010:  # ACK
            self.ntw.sendTcp4(pkt.ip_src_addr, pkt.tcp_srcPort, pkt.tcp_dstPort, b'', pkt.tcp_ack_num, pkt.tcp_seq_num + len(pkt.tcp_data), 0x0010)  # ACK
        elif pkt.tcp_flags & 0x0002:  # SYN
            self.ntw.sendTcp4(pkt.ip_src_addr, pkt.tcp_srcPort, pkt.tcp_dstPort, b'', pkt.tcp_seq_num, pkt.tcp_ack_num, 0x0012)  # SYN-ACK
        elif pkt.tcp_flags & 0x0018:  # PSH-ACK
            response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h1>Hello, World!</h1></body></html>'
            self.ntw.sendTcp4(pkt.ip_src_addr, pkt.tcp_srcPort, pkt.tcp_dstPort, response, pkt.tcp_ack_num, pkt.tcp_seq_num + len(pkt.tcp_data), 0x0018)  # PSH-ACK
            self.ntw.sendTcp4(pkt.ip_src_addr, pkt.tcp_srcPort, pkt.tcp_dstPort, b'', pkt.tcp_ack_num + len(response), pkt.tcp_seq_num + len(pkt.tcp_data), 0x0001)  # FIN-ACK

if __name__ == '__main__':
    # Create network
    nicSpi = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(11), miso=Pin(8))
    nicCsPin = Pin(13)
    ntw = Ntw.Ntw(nicSpi, nicCsPin)

    # Create DHCP client
    from machine import unique_id
    hostname = 'RPico-' + str(struct.unpack_from('I', unique_id()[-4:])[0])
    dhcp_client = Dhcp4Client.Dhcp4Client(ntw, hostname)

    # Create Web Server
    web_server = WebServer(ntw)

    while True:
        ntw.rxAllPkt()
        dhcp_client.loop()

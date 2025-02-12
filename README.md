# micropy-ENC28J60
ENC28J60 Ethernet chip driver for MicroPython v1.17 (RP2)

## Rationale
ENC28J60 is a popular and cheap module for DIY projects.
At the moment, however, there is no driver for the MicroPython environment.
The Python implementation seems easy for further improvements and self adaptation.

## Installation
Copy enc28j60.py to your board into /enc28j60 directory.

## Wiring
Wiring requires pins for SPI: SCK, MISO, MOSI and ChipSelect and optionally Interrupt.
Example wiring that uses SPI1 bus (any SPI bus can be used):

| ENC28J60 Module | RP2040 Board | Notes |
| :-------------: |:-------------:| ---- |
| VCC | 3V3 | requires up to 180 mA |
| GND | GND | |
| SCK | GP10 | SPI1 SCK |
| SI | GP11 | SPI1 MOSI/TX |
| SO | GP8 | SPI1 MISO/RX |
| CS | GP13 | SPI1 CSn |
| INT | GP15 | Optional |

## To do
 - interrupt handler


## Example code

### Packet transmission
Example of packet transmission to broadcast ethernet address:

```python
from machine import Pin, SPI
from enc28j60 import enc28j60

spi1 = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(11), miso=Pin(8))
eth = enc28j60.ENC28J60(spi1, Pin(13))
eth.init()

srcMac = eth.getMacAddr()
tgtMac = bytearray([0xFF,0xFF,0xFF,0xFF,0xFF,0xFF])
payLoad = bytearray(64)
pktType = bytearray([(len(payLoad) >> 8) & 0xFF, len(payLoad) & 0xFF])

eth.SendPacket([tgtMac, srcMac, pktType, payLoad])
```

### Packet reception
Example of packet reception:

```python
from machine import Pin, SPI
from enc28j60 import enc28j60

spi1 = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(11), miso=Pin(8))
eth = enc28j60.ENC28J60(spi1, Pin(13))
eth.init()

print("myMac:", ":".join("{:02x}".format(c) for c in eth.getMacAddr()))
print("ENC28J60 revision ID: 0x{:02x}".format(eth.GetRevId()))

rxBuf = bytearray(enc28j60.ENC28J60_ETH_RX_BUFFER_SIZE)

while eth.GetRxPacketCnt():
    rxLen = eth.ReceivePacket(rxBuf)
    print('rxLen:', rxLen, 'srcMac:', ":".join("{:02x}".format(c) for c in rxBuf[6:12]))
```

### IPv4 simple suite for polling mode

Please refer to examples/Ntw.py file for details.

The file contains roughly written procedures for handling IP protocols in polling mode:
- IPv4 for not fragmented packets only, single static IP address
- ARP for IPv4 over Ethernet, simple ARP table
- ICMPv4: rx Echo Request and tx Echo Response
- UDPv4: rx and tx
- Simple UDP Echo server

MicroPython v1.17 for Raspberry Pi Pico does not include socket library.
It also does not allow to run more than 2 threads at the time.
It is hard to mimic network sockets in such environment. So polling mode seems reasonable solution.

```python
from machine import Pin
from machine import SPI
import Ntw

if __name__ == '__main__':
    # Create network
    nicSpi = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(11), miso=Pin(8))
    nicCsPin = Pin(13)
    ntw = Ntw.Ntw(nicSpi, nicCsPin)

    # Create UDP Echo server
    udpecho = Ntw.Udp4EchoServer(ntw)

    # Bind UDP Echo server to UDP port 7
    ntw.registerUdp4Callback(7, udpecho)

    # main loop
    while True:
        # Receive and process packets
        ntw.rxAllPkt()
```

### Web Server Example

This example shows how to use the `Ntw` module to create a simple web server that serves a static HTML page. The web server listens on port 80 and uses the DHCP client for automatic IP configuration.

```python
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
```

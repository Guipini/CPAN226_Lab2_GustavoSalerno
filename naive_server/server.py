# This program was modified by Gustavo Guidini Salerno / N01648740
import socket
import argparse
import struct  # IMPROVEMENT: Import struct to unpack sequence numbers from packet headers

def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 2. Bind the socket to the port (0.0.0.0 means all interfaces)
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save each received file as 'received_<ip>_<port>.jpg' based on sender.")
    sock.bind(server_address)

    # 3. Keep listening for new transfers
    try:
        while True:
            f = None
            sender_filename = None
            expected_seq_num = 0  # IMPROVEMENT: Track the next expected sequence number for in-order delivery
            buffer = {}  # IMPROVEMENT: Dictionary to store out-of-order packets {seq_num: data} for reordering
            while True:
                data, addr = sock.recvfrom(4096)

                if len(data) < 4:  # IMPROVEMENT: Skip packets too small to contain a valid 4-byte sequence header
                    print(f"[!] Received packet too short from {addr}. Ignoring.")  # IMPROVEMENT: Log malformed packet
                    continue  # IMPROVEMENT: Ignore malformed packets and keep listening

                seq_num = struct.unpack('!I', data[:4])[0]  # IMPROVEMENT: Extract 4-byte sequence number from packet header
                payload = data[4:]  # IMPROVEMENT: Extract the actual file data after the sequence header

                ack_packet = struct.pack('!I', seq_num)  # IMPROVEMENT: Pack sequence number as ACK response
                sock.sendto(ack_packet, addr)  # IMPROVEMENT: Send ACK back to sender for every received packet

                # Protocol: If we receive an empty payload, it means "End of File"
                if not payload:  # IMPROVEMENT: Empty payload (header only) signals end of file transfer
                    print(f"[*] EOF signal (seq {seq_num}) received from {addr}. Transfer complete.")  # IMPROVEMENT: Log EOF receipt
                    break  # IMPROVEMENT: Exit receive loop for this file transfer
                if f is None:
                    print("==== Start of reception ====")
                    ip, sender_port = addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, 'wb')
                    print(f"[*] First packet received from {addr}. File opened for writing as '{sender_filename}'.")
                # Write data to disk using reordering buffer logic
                if seq_num == expected_seq_num:  # IMPROVEMENT: This is the next packet we need in sequence
                    f.write(payload)  # IMPROVEMENT: Write in-order payload directly to file
                    expected_seq_num += 1  # IMPROVEMENT: Advance to next expected sequence number

                    while expected_seq_num in buffer:  # IMPROVEMENT: Flush any consecutive buffered packets now in order
                        f.write(buffer.pop(expected_seq_num))  # IMPROVEMENT: Write buffered packet to file and remove from buffer
                        expected_seq_num += 1  # IMPROVEMENT: Continue advancing through consecutive buffered packets
                elif seq_num > expected_seq_num:  # IMPROVEMENT: Packet arrived too early (out of order)
                    buffer[seq_num] = payload  # IMPROVEMENT: Store future packet in buffer for later writing
                    print(f"[*] Buffered out-of-order packet {seq_num} (expecting {expected_seq_num})")  # IMPROVEMENT: Log buffering event

                else:  # IMPROVEMENT: seq_num < expected means this is a duplicate packet
                    pass  # IMPROVEMENT: Ignore duplicate data since ACK was already sent above
            if f:
                f.close()

            print(f"[*] Received {expected_seq_num} packets. File saved as '{sender_filename}'.")  # IMPROVEMENT: Log total packets received
            print("==== End of reception ====")
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()
        print("[*] Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Receiver")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")

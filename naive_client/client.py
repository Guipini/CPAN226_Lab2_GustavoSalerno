# This program was modified by Gustavo Guidini Salerno / N01648740
import socket
import argparse
import os
import struct  # IMPROVEMENT: Import struct module to pack sequence numbers into binary packet headers

def run_client(target_ip, target_port, input_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)  # IMPROVEMENT: Set 500ms timeout for waiting on ACKs; triggers retransmit on expiry
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    sequence_number = 0  # IMPROVEMENT: Initialize sequence counter to tag each packet with its order
    max_retries = 50  # IMPROVEMENT: Cap retransmission attempts to avoid infinite loops on persistent failure

    try:
        with open(input_file, 'rb') as f:
            while True:
                # Read a chunk of the file
                chunk = f.read(4092)  # IMPROVEMENT: Reduced from 4096 to 4092 to fit 4-byte sequence header within relay's 4096-byte buffer

                if not chunk:
                    # End of file reached
                    break

                header = struct.pack('!I', sequence_number)  # IMPROVEMENT: Pack sequence number as 4-byte big-endian unsigned int
                packet = header + chunk  # IMPROVEMENT: Combine sequence header with file data to form complete packet

                retries = 0  # IMPROVEMENT: Track number of retransmission attempts for this packet

                while retries < max_retries:  # IMPROVEMENT: Stop-and-Wait retry loop until ACK received or max retries
                    sock.sendto(packet, server_address)  # IMPROVEMENT: Send the sequenced packet to server or relay

                    try:
                        ack_data, _ = sock.recvfrom(4096)  # IMPROVEMENT: Block waiting for ACK packet from server
                        ack_num = struct.unpack('!I', ack_data)[0]  # IMPROVEMENT: Unpack the acknowledged sequence number from ACK

                        if ack_num == sequence_number:  # IMPROVEMENT: Verify ACK matches the packet we sent
                            break  # IMPROVEMENT: Correct ACK received, exit retry loop
                    except socket.timeout:  # IMPROVEMENT: No ACK within 500ms, packet or ACK was likely lost
                        retries += 1  # IMPROVEMENT: Increment retry counter
                        print(f"[!] Timeout for packet {sequence_number}, retransmitting... (attempt {retries})")  # IMPROVEMENT: Log retransmission event

                if retries >= max_retries:  # IMPROVEMENT: Check if all retry attempts exhausted
                    print(f"[!] Failed to send packet {sequence_number} after {max_retries} attempts. Aborting.")  # IMPROVEMENT: Log transfer failure
                    return  # IMPROVEMENT: Abort file transfer on persistent failure

                sequence_number += 1  # IMPROVEMENT: Increment sequence number for next packet after successful ACK

        # IMPROVEMENT: Send EOF signal as a packet with sequence header but empty payload
        eof_header = struct.pack('!I', sequence_number)  # IMPROVEMENT: Pack the final sequence number for EOF marker
        retries = 0  # IMPROVEMENT: Reset retry counter for EOF packet delivery
        while retries < max_retries:  # IMPROVEMENT: Stop-and-Wait retry loop for reliable EOF delivery
            sock.sendto(eof_header, server_address)  # IMPROVEMENT: Send EOF packet (header only, no data payload)
            try:
                ack_data, _ = sock.recvfrom(4096)  # IMPROVEMENT: Wait for server to acknowledge EOF
                ack_num = struct.unpack('!I', ack_data)[0]  # IMPROVEMENT: Unpack the EOF ACK sequence number
                if ack_num == sequence_number:  # IMPROVEMENT: Confirm the server acknowledged our EOF signal
                    print("[*] File transfer complete.")  # IMPROVEMENT: Log successful EOF confirmation
                    break  # IMPROVEMENT: EOF confirmed, transfer is complete
            except socket.timeout:  # IMPROVEMENT: EOF ACK was lost or delayed
                retries += 1  # IMPROVEMENT: Increment EOF retry counter
                print(f"[!] Timeout for EOF packet, retransmitting... (attempt {retries})")  # IMPROVEMENT: Log EOF retransmission

        print(f"[*] File transfer complete. Sent {sequence_number} packets.")  # IMPROVEMENT: Log transfer summary with total packet count

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Sender")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)

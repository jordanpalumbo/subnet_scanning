#----IMPORTS----
import concurrent.futures
import ipaddress
import os 
import platform
import subprocess
import time 
#---------------

current_os = platform.system().lower()

def ping_host(ip, timeout=1.0):
    """Pings a single IP address and returns its status."""
    ip_str = str(ip)

    if current_os == "windows":
        # -n: number of packets, -w: timeout in milliseconds
        command = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip_str]

    else:
        # -c: packets to send, -W: timeout in milliseconds
        command = ["ping", "-c", "1", "-W", str(timeout), ip_str]

    try:
        #Runs command and redirect output to suppress console clutter
        result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout= timeout + 0.5
                )
        #return code 0 means successful reply
        if result.returncode == 0:
            return ip_str, True
    except (subprocess.TimeoutExpired, Exception):
        pass
        
    return ip_str, False


def main():
    print("=" * 50)
    print("Multithreaded Ping Sweeper")
    print("=" * 50)

    #User input for network address
    network_address = input("Enter network address: (e.g. 192.168.1.0/24): ").strip()

    try:
        #Parsing network using built-in ipaddress module
        network = ipaddress.ip_network(network_address, strict=False)
        print(f"\n[+] Scanning network: {network}")
        print(f"[+] Total potential hosts: {network.num_addresses - 2 if network.prefixlen < 31 else network.num_addresses}")
        print("[+] Please wait...")

    except ValueError:
        print("[!] Invalid network address or CIDR notation. Exiting...")
        return

    start_time = time.time()
    live_hosts = []

    #Using ThreadPoolExecutor for concurrent ping execution

    max_workers = 100 
    
    #Extract only valuid target hosts (skipping network and broadcast addresses)
    hosts_to_scan = list(network.hosts()) if network.prefixlen < 31 else [network.network_address]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        #Map ping function over the host collection
        future_to_ip = {executor.submit(ping_host, ip): ip for ip in hosts_to_scan}

        for future in concurrent.futures.as_completed(future_to_ip):
            ip_str, is_alive = future.result()
            if is_alive:
                print(f"[+] Host active: {ip_str}")
                live_hosts.append(ip_str)

    end_time = time.time()
    duration = end_time - start_time

    #Display final report metrics
    print("\n" + "=" * 50)
    print(" Scan Results Summary")
    print("=" * 50)
    print(f"[-] Scan Duration: {duration:.2f} seconds")
    print(f"[-] Total Live Hosts Found: {len(live_hosts)}")
    print("-" * 50)
    
    for host in sorted(live_hosts, key=ipaddress.IPv4Address):
        print(f" -> {host}")

if __name__ == "__main__":
    main()

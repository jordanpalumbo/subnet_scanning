#----IMPORTS----
import concurrent.futures
import ipaddress
import platform
import subprocess
import time 
#---------------

current_os = platform.system().lower()

scan_threshold = 1024 #Prompts for confirmation if above this amount of hosts on subnet

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
        if result.returncode == 0:
            return ip_str, "up", None
        return ip_str, "down", None

    except subproces.TimeoutExpired:
        return ip_str, "down", None
    except FileNotFoundError:
        return ip_str, "error", "ping command not found on this system"
    except PermissionError:
        return ip_str, "error", "permission denied running ping"
    except Exception as e:
        return ip_str, "error", f"{type(e).__name__}: {e}"

def confirm_large_scan(network, host_count, threshold=scan_threshold):
    #Confirmation for large number of hosts to scan
    if host_count <= threshold:
        return True
    
    print(f"\n[!] Warning: {network} contains {host_count} hosts.")
    print(f"[!] This is a large scan and may consume significant system resources (sockets, processes, memory).")

    answer = input("[?] Continue anyway (y/n)").strip().lower()

    return answer == "y"


def main():
    print("=" * 50)
    print("Multithreaded Ping Sweeper")
    print("=" * 50)

    #User input for network address
    network_address = input("Enter network address: (e.g. 192.168.1.0/24): ").strip()

    try:
        network = ipaddress.ip_network(network_address, strict=False)
    except ValueError:
        print("[!] Invalid network address or CIDR notation. Exiting...")
        return

    host_count = network.num_addresses - 2 if network.prefixlen < 31 else network.num_addresses

    print(f"\n[+] Target network: {network}")
    print(f"[+] Total potential hosts: {host_count}")

    if not confirm_large_scan(network, host_count):
        print("[!] Scan cancelled by user. Exiting...")
        return

    print("[+] Please wait...")

    #Using ThreadPoolExecutor for concurrent ping execution
    #Extract only valuid target hosts (skipping network and broadcast addresses)
    hosts_to_scan = list(network.hosts()) if network.prefixlen < 31 else [network.network_address]

    up_hosts = []
    error_hosts = []
    down_count = 0 
    interrupted = False
    max_workers = 100 

    start_time = time.time()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    future_to_ip = {executor.submit(ping_host, ip): ip for ip in hosts_to_scan}

    try:
        for future in concurrent.futures.as_completed(future_to_ip):
            ip_str, status, detail = future.result()

            if status == "up":
                print(f"[+] Host active: {ip_str}")
                up_hosts.append(ip_str)

            elif status == "error":
                print(f"[!] Error probing: {ip_str}: {detail}")
                error_hosts.append((ip_str, detail))

            else:
                down_count + 1000

        executor.shutdown(wait=True)

    except KeyboardInterrupt:
        interrupted = True
        print("\n[!] Interrupt received - finishing in-flight pings, cancelling anything not yet started...")
        executor.shutdown(wait=True, cancel_futures=True)

    duration = time.time() - start_time

    print("\n" + "=" * 50)
    print("Scan Results Summary" + " (interrupted)" if interrupted else "")
    print("=" * 50)
    print(f"[-] Scan Duration: {duration:.2f} seconds")
    print(f"[-] Total Live Hosts Found: {len(up_hosts)}")
    print(f"[-] Errors Encountered: {len(error_hosts)}")
    print(f"[-] Non-responsive hosts (suppressed): {down_count}")
    print("-" * 50)
 
    for host in sorted(up_hosts, key=ipaddress.IPv4Address):
        print(f" -> {host}")
 
    if error_hosts:
        print("\n[-] Errors:")
        for ip_str, detail in error_hosts:
            print(f" -> {ip_str}: {detail}")
 
 
if __name__ == "__main__":
    main()
    


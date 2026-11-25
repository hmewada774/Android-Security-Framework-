#!/usr/bin/env python3
import sys
import argparse
import asyncio
from pathlib import Path

# Add project root to sys.path so modules resolve cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from controller.commands import (
    check_health,
    init_pairing,
    list_devices,
    revoke_device,
    monitor_events,
    DEFAULT_BACKEND_URL,
)

def print_banner():
    banner = r"""
=========================================================
      ANDROID SECURITY FRAMEWORK (ASF) — CONTROLLER     
=========================================================
"""
    print(banner)

def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--url",
        default=DEFAULT_BACKEND_URL,
        help=f"Target backend base URL (default: {DEFAULT_BACKEND_URL})",
    )

    parser = argparse.ArgumentParser(
        description="ASF Security Terminal Controller - Control and monitor authorized Android test devices.",
        parents=[parent_parser],
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # health
    subparsers.add_parser("health", parents=[parent_parser], help="Check backend health and SQLite database state")

    # pair
    pair_parser = subparsers.add_parser("pair", parents=[parent_parser], help="Generate a one-time 6-digit pairing PIN")
    pair_parser.add_argument("--name", default="Authorized Test Device", help="Device label")

    # devices
    subparsers.add_parser("devices", parents=[parent_parser], help="List all paired devices")

    # revoke
    revoke_parser = subparsers.add_parser("revoke", parents=[parent_parser], help="Revoke device pairing token")
    revoke_parser.add_argument("device_id", help="Device ID to revoke")

    # monitor
    subparsers.add_parser("monitor", parents=[parent_parser], help="Open real-time terminal event monitor via WebSocket")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    base_url = args.url

    if args.command == "health":
        res = check_health(base_url)
        print("[*] Health Check Result:")
        print(f"    Status:   {res.get('status', 'ERROR')}")
        print(f"    Version:  {res.get('version', 'N/A')}")
        print(f"    Database: {res.get('database', 'N/A')}")
        print(f"    Details:  {res.get('details', {})}")

    elif args.command == "pair":
        res = init_pairing(args.name, base_url)
        if res.get("error"):
            print(f"[!] Error: {res}")
        else:
            print("[+] Pairing Initialized Successfully:")
            print(f"    ------------------------------------")
            print(f"    PIN:                {res.get('pairing_pin')}")
            print(f"    Expires in:         {res.get('expires_in_seconds')} seconds (5 mins)")
            print(f"    ------------------------------------")
            print(f"    Enter this PIN in the ASF Android application to pair your device.")

    elif args.command == "devices":
        res = list_devices(base_url)
        if isinstance(res, list):
            print(f"[*] Paired Devices ({len(res)} total):")
            for d in res:
                status_color = "[ACTIVE]" if d.get("status") == "paired" else f"[{d.get('status').upper()}]"
                print(f"    - ID:     {d.get('device_id')}")
                print(f"      Name:   {d.get('device_name')} ({d.get('model')}, {d.get('os_version')})")
                print(f"      Status: {status_color}")
                print(f"      Seen:   {d.get('last_seen_at') or 'Never'}\n")
            if not res:
                print("    (No devices paired yet)")
        else:
            print(f"[!] Failed to list devices: {res}")

    elif args.command == "revoke":
        res = revoke_device(args.device_id, base_url)
        print(f"[*] Revoke response: {res}")

    elif args.command == "monitor":
        try:
            asyncio.run(monitor_events(base_url))
        except KeyboardInterrupt:
            print("\n[*] Exited monitor.")

if __name__ == "__main__":
    main()

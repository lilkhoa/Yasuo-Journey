import sys
import os
import argparse

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.game import run

def main():
    parser = argparse.ArgumentParser(
        description="A3 Yasuo - run single-player or 2-player co-op over LAN."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--host",
        action="store_true",
        help="Start as 2-player HOST (server + player 1).",
    )
    mode_group.add_argument(
        "--client",
        metavar="HOST_IP",
        help="Join as GUEST (player 2), connecting to the given server IP.",
    )
    args = parser.parse_args()

    if args.host:
        print("[Launcher] Starting in HOST mode …")
        run(net_mode="host")
    elif args.client:
        print(f"[Launcher] Connecting to {args.client} as CLIENT …")
        run(net_mode="client", host_ip=args.client)
    else:
        # Default: single-player (no networking)
        run(net_mode="solo")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
parse_country_db.py

Parses IP location CSV databases (from @ip-location-db / sapics)
and generates sorted, deduplicated CIDR block lists (.lst) for specified countries.

Input format: start_ip, end_ip, country_code [, ...]
Output files: <output-dir>/<prefix><country_code>.lst
"""

import argparse
import csv
import ipaddress
import sys
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert IP-to-Country CSV ranges to CIDR block lists."
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path, help="Path to input CSV file"
    )
    parser.add_argument(
        "-c",
        "--countries",
        required=True,
        type=str,
        help="Comma-separated country codes to filter (e.g. RU,BY)",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        default="",
        type=str,
        help="Prefix for generated .lst filenames (e.g. 'geolite_' or 'dbip_')",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=Path("."),
        type=Path,
        help="Target directory for output .lst files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    target_countries = {c.strip().upper() for c in args.countries.split(",") if c.strip()}
    if not target_countries:
        print("Error: No valid country codes provided.", file=sys.stderr)
        sys.exit(1)

    if not args.input.is_file():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    networks_by_country: dict[str, list[str]] = defaultdict(list)

    print(f"Processing '{args.input}' for countries: {', '.join(sorted(target_countries))}...")

    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)

        # Skip header if present
        first_row = next(reader, None)
        if first_row:
            try:
                ipaddress.ip_address(first_row[0].strip())
                # First row is data, process it
                _process_row(first_row, target_countries, networks_by_country)
            except ValueError:
                # First row is a header, proceed to next rows
                pass

        for row in reader:
            _process_row(row, target_countries, networks_by_country)

    # Write output files
    for country_code in sorted(target_countries):
        raw_list = networks_by_country[country_code]
        # Deduplicate and sort by IP address
        unique_nets = sorted(
            set(raw_list),
            key=lambda x: (ipaddress.ip_network(x).version, int(ipaddress.ip_network(x).network_address), ipaddress.ip_network(x).prefixlen)
        )
        out_filename = f"{args.prefix}{country_code.lower()}.lst"
        out_path = args.output_dir / out_filename

        with open(out_path, "w", encoding="utf-8", newline="\n") as out_f:
            for net in unique_nets:
                out_f.write(f"{net}\n")

        print(f"  -> Wrote {len(unique_nets):>6} CIDRs to '{out_path}'")


def _process_row(
    row: list[str],
    target_countries: set[str],
    networks_by_country: dict[str, list[str]],
) -> None:
    if len(row) < 3:
        return

    country = row[2].strip().upper()
    if country not in target_countries:
        return

    start_str = row[0].strip()
    end_str = row[1].strip()

    try:
        start_ip = ipaddress.ip_address(start_str)
        end_ip = ipaddress.ip_address(end_str)
        if start_ip.version != end_ip.version or start_ip > end_ip:
            return

        for net in ipaddress.summarize_address_range(start_ip, end_ip):
            networks_by_country[country].append(str(net))
    except ValueError:
        return


if __name__ == "__main__":
    main()

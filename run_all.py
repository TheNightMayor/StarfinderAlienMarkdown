import argparse
import subprocess
import sys


def run_command(command, description):
    print(f"\n==> {description}")
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run the full data pipeline: download URL list, download pages, get classes, and generate markdown."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to the data directory (default: data)",
    )
    parser.add_argument(
        "--skip-download-list",
        action="store_true",
        help="Skip the URL list download step.",
    )
    parser.add_argument(
        "--skip-download-pages",
        action="store_true",
        help="Skip the page download step.",
    )
    parser.add_argument(
        "--skip-classes",
        action="store_true",
        help="Skip the class hit point download step.",
    )
    parser.add_argument(
        "--skip-main",
        action="store_true",
        help="Skip the markdown generation step.",
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Optional URL to pass to download_page_list.py. If omitted, the default URL list is used.",
    )

    args = parser.parse_args()
    python = sys.executable
    data_dir = args.data_dir

    if not args.skip_download_list:
        cmd = [python, "download_page_list.py"]
        if args.url:
            cmd.extend(args.url)
        run_command(cmd, "Downloading page list")

    if not args.skip_download_pages:
        cmd = [python, "download_pages.py", data_dir]
        run_command(cmd, "Downloading individual pages")

    if not args.skip_classes:
        cmd = [python, "get_classes.py"]
        run_command(cmd, "Downloading class hit points")

    if not args.skip_main:
        cmd = [python, "main.py", data_dir]
        run_command(cmd, "Generating markdown files")

    print("\nAll steps finished.")


if __name__ == "__main__":
    main()

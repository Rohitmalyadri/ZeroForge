import argparse


VERSION = "0.1.0"


def create_parser():
    parser = argparse.ArgumentParser(
        prog="zeroforge",
        description="ZeroForge - Zero-dependency task scheduling engine"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ZeroForge {VERSION}"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands"
    )

    # add command
    add_parser = subparsers.add_parser(
        "add",
        help="Create a new task"
    )

    add_parser.add_argument(
        "title",
        help="Task title"
    )

    return parser


def add_task(args):
    print(f"Creating task: {args.title}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "add":
        add_task(args)


if __name__ == "__main__":
    main()
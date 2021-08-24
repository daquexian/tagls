import argparse

import tagls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcp", action="store_true")
    parser.add_argument("--port", type=int, default=9528)

    args = parser.parse_args()

    if args.tcp:
        tagls.server.start_tcp("127.0.0.1", args.port)
    else:
        tagls.server.start_io()


if __name__ == '__main__':
    main()

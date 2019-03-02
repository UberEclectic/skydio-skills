"""
Payload Support

Allow the vehicle to takeoff with it's USB-C port in use.

Run the script once to make this behavior default for your vehicle.

Run the script with --disable to revert R1 to the original settings.
"""
from __future__ import absolute_import
from __future__ import print_function
import argparse

from skydio.comms.http_client import HTTPClient

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseurl', default='http://192.168.10.1',
                        help='The url of the vehicle.')
    parser.add_argument('--disable', action='store_true',
                        help='Disable payload mode')
    args = parser.parse_args()
    client = HTTPClient(args.baseurl, pilot=True)

    if args.disable:
        print('Disabling payload mode...')
        mode = 'IRL_PRODUCT'
    else:
        print('Enabling payload mode...')
        mode = 'IRL_PRODUCT_PAYLOAD'
    client.set_run_mode(mode, set_default=True)
    print('Done')


if __name__ == '__main__':
    main()


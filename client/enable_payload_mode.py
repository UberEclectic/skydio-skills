"""
Payload Support

Allow the vehicle to takeoff with it's USB-C port in use.

It is expected to run this script from the USB-C connected device which should see the vehicle at 192.168.13.1.
"""
from __future__ import absolute_import
from __future__ import print_function
import argparse

from skydio.comms.http_client import HTTPClient

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseurl', default='http://192.168.13.1',
                        help='The url of the vehicle.')
    args = parser.parse_args()
    client = HTTPClient(args.baseurl, pilot=True)
    print('Enabling payload mode...')
    client.set_run_mode('IrlProductEnterprise')
    print('Done')


if __name__ == '__main__':
    main()


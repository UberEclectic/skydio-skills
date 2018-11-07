"""
SkillClient
"""
from __future__ import absolute_import
import argparse
import base64
import json
import sys
import time
import urllib2


def fmt_out(fmt, *args, **kwargs):
    """ Helper for printing formatted text to stdout. """
    sys.stdout.write(fmt.format(*args, **kwargs))
    sys.stdout.flush()


def fmt_err(fmt, *args, **kwargs):
    """ Helper for printing formatted text to stderr. """
    sys.stderr.write(fmt.format(*args, **kwargs))
    sys.stderr.flush()


class SkillClient(object):
    """
    HTTP client for communicating with a Skill running on a Skydio drone.

    Use this to connect a laptop over Wifi or an onboard computer over ethernet.

    Args:
        baseurl (str): the url of the vehicle.
            If you're directly connecting to a real R1 via WiFi, use 192.168.10.1
            If you're connected to a simulator over the Internet, use https://sim####.sim.skydio.com
        skill_key (str): the unique identifier for your Skill.
            If you're Skill is not active, messages will be dropped.
            Example: samples.com_link.ComLink
    """

    def __init__(self, baseurl, skill_key):
        self.baseurl = baseurl
        self.skill_key = skill_key

    def post_json(self, endpoint, json_data, timeout=20):
        url = '{}/api/{}'.format(self.baseurl, endpoint)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        request = urllib2.Request(url, json.dumps(json_data), headers=headers)
        response = urllib2.urlopen(request, timeout=timeout)
        status_code = response.getcode()
        status_code_class = int(status_code / 100)
        if status_code_class in [4, 5]:
            raise urllib2.HTTPError(url, status_code, '{} Client Error'.format(status_code),
                                    response.info(), response)
        # Ensure that the request is a file like object with a read() method.
        # We've seen instances where urlopen does not raise an exception, but we cannot read it.
        if not callable(getattr(response, 'read', None)):
            raise IOError('urlopen response has no read() method')

        server_response = json.loads(response.read())
        if 'data' not in server_response:
            # The server detected an error. Display it.
            raise RuntimeError('No response data: {}'.format(server_response.get('error')))
        return server_response['data']

    def send_custom_comms(self, data, ack=True, request_id=0):
        """
        Send custom bytes to the vehicle and optionally return a response

        Args:
            skill_key (str): The identifer for the Skill you want to receive this message.
            data (bytes): The payload to send.
            ack (bool): Set this to False if you don't want a response.
            request_id (int): an optional id for your request that will be included in the response.

        Returns:
            dict: a dict with metadata for the response and a 'data' field, encoded by the Skill.
        """

        request_rpc = {
            'ack': ack,
            'requestId': request_id,
            'skillKey': self.skill_key,
            'data': base64.b64encode(data),
            'utime': int(time.time() * 1e6),
            'version': 1,
        }

        # Post rpc to the server as json.
        try:
            response_rpc = self.post_json('custom_comms', request_rpc)
        except Exception as error:  # pylint: disable=broad-except
            fmt_err('Error {}', error)
            return {'requestId': request_id, 'status': 'EXCEPTION'}

        # Parse and return the rpc.
        if response_rpc:
            if 'data' in response_rpc:
                response_rpc['data'] = base64.b64decode(response_rpc['data'])
        return response_rpc


def main():
    parser = argparse.ArgumentParser(description="Example command-line interface for a Skill.")
    parser.add_argument('--baseurl', metavar='URL', default='http://192.168.10.1',
                        help='the url of the vehicle')
    parser.add_argument('--skill_key', metavar='KEY', default='samples.com_link.ComLink',
                        help='the skill to communicate with')
    parser.add_argument('--title', default='Hello World',
                        help='set the title on the phone')
    parser.add_argument('--forward', metavar='X', type=float,
                        help='move forward X meters.')
    parser.add_argument('--loop', action='store_true',
                        help='keep sending messages')
    args = parser.parse_args()

    client = SkillClient(args.baseurl, args.skill_key)

    # Example usage: repeatedly send some data and print the response.
    start_time = time.time()
    while 1:
        request = {
            'title': args.title,
            'detail': int(time.time() - start_time),
        }
        if args.forward:
            request['forward'] = args.forward

        fmt_out('Request {}\n', request)

        # Arbitrary data format. Using JSON here.
        data = json.dumps(request)

        response = client.send_custom_comms(data)
        fmt_out('Response {}\n', json.dumps(response, sort_keys=True, indent=True))

        if args.loop:
            # Rate-limit to prevent overloading the vehicle.
            time.sleep(1)
        else:
            break


if __name__ == '__main__':
    main()

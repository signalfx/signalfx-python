import getpass
import json
import os
import re

try:
    import urllib2
except ImportError:
    import urllib.request
    # This usage is generally correct for this script
    urllib2 = urllib.request
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Helper script that gives you all the access tokens your account has.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--url', default='https://api.signalfuse.com', help='SignalFX endpoint')
    parser.add_argument('--password', default=None, help='Optional command line password')
    parser.add_argument('--org', default=None,
                        help='If set, change output to only the auth token of this org')
    parser.add_argument('--update', default=None,
                        help='If set, will look for a collectd file and auto update to the auth token you select.')
    parser.add_argument('user_name', help="User name to log in with")

    args = parser.parse_args()

    if args.update is not None:
        assert os.path.isfile(args.update), "Unable to find the file to update: " + args.update

    if args.password is None:
        args.password = getpass.getpass('SignalFX password: ')

    # Get the session
    json_payload = {"email": args.user_name, "password": args.password}
    headers = {'content-type': 'application/json'}
    req = urllib2.Request(args.url + "/session", json.dumps(json_payload), headers)
    try:
        resp = urllib2.urlopen(req)
    except urllib2.HTTPError:
        sys.stderr.write("Invalid user name/password\n")
        sys.exit(1)
    res = resp.read()
    sf_accessToken = json.loads(res)['sf_accessToken']
    sf_userID = json.loads(res)['sf_userID']

    # Get the orgs
    orgs_url = args.url + "/orguser?query=sf_userID:%s" % sf_userID
    headers = {'content-type': 'application/json', 'X-SF-TOKEN': sf_accessToken}
    req = urllib2.Request(orgs_url, headers=headers)
    resp = urllib2.urlopen(req)
    res = resp.read()
    all_res = json.loads(res)
    printed_org = False
    all_auth_tokens = []
    for i in all_res['rs']:
        if args.org is not None:
            if args.org == i['sf_organization']:
                all_auth_tokens.append((i['sf_organization'], i['sf_apiAccessToken']))
                sys.stdout.write(i['sf_apiAccessToken'])
                printed_org = True
        else:
            all_auth_tokens.append((i['sf_organization'], i['sf_apiAccessToken']))
            print ("%40s%40s" % (i['sf_organization'], i['sf_apiAccessToken']))
    if args.org is not None and not printed_org:
        sys.stderr.write("Unable to find the org you set.\n")
        sys.exit(1)
    if args.update is None:
        sys.exit(0)
    assert len(all_auth_tokens) != 0
    if len(all_auth_tokens) > 1:
        sys.stderr.write(
            "Multiple auth tokens associated with this account.  Add an --org tag for the auth token you want to update to.\n")
        examples = ["get_all_auth_tokens.py --org=%s" % s[0] for s in all_auth_tokens]
        sys.stderr.write("\n".join(examples))
        sys.exit(1)

    replace_in_file(args.update, 'APIToken "(.*)"', 'APIToken "%s"' % all_auth_tokens[0][1])


def decode_string(str_to_decode):
    try:
        return str_to_decode.decode("UTF-8")
    except AttributeError:
        return str_to_decode


def replace_in_file(file_name, regex_to_change, new_subpart):
    p = re.compile(regex_to_change)
    with open(file_name, 'rb') as f:
        old_file_contents = decode_string(f.read())

    (new_file_contents, num_replacements) = p.subn(new_subpart, old_file_contents)
    if num_replacements != 1:
        raise Exception("Invalid file format.  Please do auth token replacement manually")

    encoded_new_contents = new_file_contents.encode("UTF-8")
    with open(file_name, 'wb') as f:
        f.write(encoded_new_contents)


if __name__ == '__main__':
    main()

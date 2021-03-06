#!/usr/bin/env python3

import os
import requests
import shutil
import statistics
import subprocess
import time
import yaml


def convert_to_point(line):
    """Convert an fping output line to InfluxDB line protocol."""
    host = line.split(':')[0].rstrip()

    pings = line.split(':')[1].lstrip().split(' ')
    pings = [float(ping) for ping in pings if ping != '-']

    if len(pings) == 0:
        return

    minimum = min(pings)
    average = "{0:.2f}".format(statistics.mean(pings))
    maximum = max(pings)
    standard_deviation = "{0:.2f}".format(statistics.pstdev(pings))
    tags = [
        'ping',
        'src=' + config['src_host_name'],
        'dest=' + host
    ]
    fields = [
        'min=' + str(minimum),
        'avg=' + str(average),
        'max=' + str(maximum),
        'sd=' + str(standard_deviation)
    ]

    return(','.join(tags) + ' ' + ','.join(fields) + ' ' + str(timestamp))


# Load the configuration.

config = yaml.safe_load(open(os.getenv('HOME')
                             + '/.config/ping-logger/config.yaml'))
concatenated_hosts = '\n'.join(config['dest_hosts'])
timestamp = int(time.time())

# Now run the test!

fping_run = subprocess.run([shutil.which('fping'), '-C',
                           str(config['ping_count']), '-q', '-R'],
                           input=concatenated_hosts, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
fping_output_lines = fping_run.stdout.splitlines()
points = []

for line in fping_output_lines:
    point = convert_to_point(line)

    if point is not None:
        points.append(point)

# Post the results to InfluxDB.

influxdb_post = requests.post(
    config['influxdb_connection']['server']
    + '/write?db='
    + config['influxdb_connection']['database']
    + '&precision=s',
    auth=(config['influxdb_connection']['username'],
          config['influxdb_connection']['password']),
    data='\n'.join(points)
)

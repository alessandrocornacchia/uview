import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import argparse
import datetime
import urllib
import os
from datacollection.utils import make_path, stream_traces, head_sampling
from utils import parse_timeframe

#endpoint = os.environ.get('JAEGER_UI_BIND_ADDR', "localhost:12349")
#JAEGER_TRACES_ENDPOINT = f"http://{endpoint}/jaeger/api/services


def download(args):
    
    JAEGER_TRACES_ENDPOINT = args['jaeger_endpoint']
    query_string = urllib.parse.urlencode(args['query'], quote_via=urllib.parse.quote)
    
    url = f'http://{JAEGER_TRACES_ENDPOINT}/api/traces?{query_string}'
    

    print(f'Connecting to {url}...')
    source = urllib.request.urlopen(url)
    print(f'Succeed...')
    return stream_traces(source, args['file'], compression=True, debug=args['debug'], overwrite=args['yes'])

def sample(args):
    head_sampling(args['file'], p=args['sampling']/100)
        

parser = argparse.ArgumentParser()

# sub-commands
subparsers = parser.add_subparsers()
parser_download = subparsers.add_parser('download', help='download traces')
parser_download.set_defaults(func=download)
parser_sample = subparsers.add_parser('sample', help='sample traces')
parser_sample.add_argument("--sampling", "-p", type=float, help="Sampling percentage", default=100)
parser_sample.set_defaults(func=sample)

# global
parser.add_argument("--service", "-s", type=str, help="Service name", default="frontend")
parser.add_argument("--operation", "-o", type=str, default='', help="Operation name")
parser.add_argument("--duration", "-d", type=int, help="Lookback/lookforward from end/start in minutes", default=None)
parser.add_argument("--limit", "-l", help="Limit", default=100000)
parser.add_argument("--file", "-f", type=str, help="Output file")
parser.add_argument("--directory", "-D", type=str, help="Output directory", required=True)
parser.add_argument("--jaeger-endpoint", "-j", type=str, help="Jaeger endpoint", default="jaeger.172.18.0.28.nip.io:31898")
parser.add_argument("--start", type=str, help="Start time")
parser.add_argument("--end", type=str, help="End time")
parser.add_argument("--yes", "-y", action='store_true', help="Automatic yes to prompts")

#---------------------------
#          program
#---------------------------

if __name__ == "__main__":
    args = parser.parse_args()

    start_time, end_time = parse_timeframe(args.start, args.end, duration=args.duration)

    query_params = {
        "service" : args.service,
        "operation" : args.operation,
        "start" : int(start_time.timestamp() * 1000000) if start_time else '',
        "end" : int(end_time.timestamp() * 1000000) if end_time else '',
        "limit" : args.limit,
        "lookback" : f'{args.duration}m' if args.duration else ''
    }

    if args.file is None:
        dir = make_path(args.directory)
        args.file = os.path.join(
            dir, 
            f'{args.service}-{args.operation}.csv.gz' if args.operation else f'{args.service}.csv.gz'
        )

    # set env variable with dir value, export such that is visible everywhere
    
    os.environ['DATASET_DIR'] = dir

    # convert args to dictionary
    args = vars(args)
    args['query'] = query_params
    args['dir'] = dir
    args['debug'] = False
    # call function
    args['func'](args)

        
        

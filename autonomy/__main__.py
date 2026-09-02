import argparse
import json

from .mission import SCENARIOS, simulate

parser = argparse.ArgumentParser(description='CARE-PACK mission simulator. No physical robot commands.')
parser.add_argument('--scenario', choices=SCENARIOS, default='success')
args = parser.parse_args()
print(json.dumps(simulate(args.scenario), ensure_ascii=False, indent=2))

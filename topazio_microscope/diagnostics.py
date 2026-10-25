import argparse, json
from pathlib import Path
from .capture.camera import scan, capture_sample

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    results = scan()
    payload = [r.__dict__ for r in results]
    good = next((r for r in results if r.frames), None)
    if good:
        out = Path(__file__).parents[1] / 'captures' / f'diagnostic_{good.index}_{good.backend.replace(" ", "_")}.png'
        try:
            capture_sample(good.index, good.backend, out)
            payload.append({'sample': str(out), 'validated': True})
        except Exception as e:
            payload.append({'validated': False, 'sample_error': str(e)})
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else '\n'.join(map(str, payload)))

if __name__ == '__main__': main()

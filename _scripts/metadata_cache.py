import os
import sys
import glob
import redis
from ruamel.yaml import YAML


r = redis.Redis(host=os.getenv('REDIS_HOST', 'sre-redis-master.teko-system'))

if os.getenv('CI_COMMIT_REF_NAME', None) != 'master':
    print('This repo support only to run on master branch')
    sys.exit(1)

yaml = YAML()


__default_workload = os.getenv('CI_PROJECT_NAME')

workload = os.getenv('workload', __default_workload)

files = [f for f in glob.glob("**/*.yaml", recursive=True)]

image_to_files = {}

print("## Update quick lookup for workload [{}]".format(workload))

for f in files:
    with open(f) as fo:
        content = yaml.load(fo.read())
        if (content is None) or ('image' not in content):
            continue
        image = content.get('image', {})
        if not isinstance(image, dict):
            continue
        image_repository = image.get('repository', '')
        # if not image_repository.startswith('hub.teko.vn'):
        # continue
        key = '{}:{}'.format(workload, image_repository)
        affected_files = image_to_files.get(key, {f})
        affected_files.add(f)
        image_to_files[key] = affected_files

for k in image_to_files:
    print('workload={} image={}'.format(workload, k[len(workload)+1:]))
    for fp in image_to_files[k]:
        print('- {}'.format(fp))
        r.sadd(k, fp)

print("\n## Look up to delete unused keys...")

for k in (
    k.decode('utf-8')
    for k in r.scan_iter('{}:*'.format(workload))
    if k.decode('utf-8') not in image_to_files
):
    r.delete(k)
    print('- key={} has been deleted'.format(k))

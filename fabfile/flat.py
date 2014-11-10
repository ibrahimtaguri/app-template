#!/usr/bin/env python

from cStringIO import StringIO
import gzip
import mimetypes
import os

import boto
from boto.s3.key import Key
from fabric.api import task

import app_config

GZIP_FILE_TYPES = ['.html', '.js', '.json', '.css', '.xml']

class FakeTime:
    def time(self):
        return 1261130520.0

# Hack to override gzip's time implementation
# See: http://stackoverflow.com/questions/264224/setting-the-gzip-timestamp-from-python
gzip.time = FakeTime()

def deploy_file(connection, src, dst, max_age):
    """
    Deploy a single file to S3.
    """
    bucket = connection.get_bucket(app_config.S3_BUCKET['bucket_name'])
    k = Key(bucket) 
    k.key = dst

    headers = {
        'Content-Type': mimetypes.guess_type(src),
        'Cache-Control': 'max-age=%i' % max_age 
    }

    if os.path.splitext(src)[1].lower() in GZIP_FILE_TYPES:
        headers['Content-Encoding'] = 'gzip'
    
        with open(src, 'rb') as f_in:
            contents = f_in.read()

        output = StringIO()
        f_out = gzip.GzipFile(filename=dst, mode='wb', fileobj=output)
        f_out.write(contents)
        f_out.close()
    
        print 'Uploading %s --> %s (gzipped)' % (src, dst)

        k.set_contents_from_string(output.getvalue(), headers, policy='public-read')
    else:
        print 'Uploading %s --> %s' % (src, dst)
        
        k.set_contents_from_filename(src, headers, policy='public-read')

@task
def deploy_folder(src, dst, max_age=app_config.DEFAULT_MAX_AGE):
    """
    Deploy a folder to S3.
    """
    to_deploy = []

    for local_path, subdirs, filenames in os.walk(src, topdown=True):
        rel_path = os.path.relpath(local_path, src)

        for name in filenames:
            if name.startswith('.'):
                continue
                
            src_path = os.path.join(local_path, name)

            if rel_path == '.':
                dst_path = os.path.join(dst, name)
            else:
                dst_path = os.path.join(dst, rel_path, name)

            to_deploy.append((src_path, dst_path))

    s3 = boto.connect_s3() 

    for src, dst in to_deploy:
        deploy_file(s3, src, dst, max_age)

    

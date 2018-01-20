#!/usr/bin/env python2
import os
import sys
import json
from argparse import ArgumentParser
import logging 
from shutil import copyfile

def main():
    """
    uploading artifacts to the s3 bucket

    """
    parser = ArgumentParser()
    parser.add_argument("-t", "--tag", dest="myTag", help="""./bin/upload_emr_ver2S3.py \
    --tag igz_1.5.0_b16_20180116095940 \n""")
    parser.add_argument("-f", "--config-file", dest="config_file", help="config file ",
                         default='./bin/upload_emr_ver2S3.json')
    args = parser.parse_args()

    if args.myTag:
        print("Current tag {}".format(args.myTag))
        action = EMRuploader(args.myTag, args.config_file)
        action.upload_artifacts_to_s3()
    else:
        print ("""
        example how to run:
        ./bin/upload_emr_ver2S3.py --tag igz_1.5.0_b16_20180116095940 --config-file ./bin/upload_emr_ver2S3.json
        """)
        sys.exit(1)


class EMRuploader:
    """
    Uploading EMR dependencies to S3 bucket
    """

    def __init__(self, tag, config_file):
        self.version = tag
        self.spark_pkgs_json = config_file
        with open(self.spark_pkgs_json, 'r') as fr:
            self.packages = json.load(fr)
            self.s3_bucket = self.packages['s3_bucket']
            self.docker_registry = self.packages['docker_registry']
            self.AUTH = self.packages['artifactory_auth']
            self.ART_URL = self.packages['artifactory_url']
            self.emr_version = self.packages['emr_version']
            self.log = logging.getLogger(__name__)
            self.out_hdlr = logging.StreamHandler(sys.stdout)
            self.out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            self.out_hdlr.setLevel(logging.INFO)
            self.log.addHandler(self.out_hdlr)
            self.log.setLevel(logging.INFO)

            self.CWD = os.getcwd()
        fr.close()

    def _download_pkgs(self):
        """ 
            download artifacts from artifactory 
        """
        for package in self.packages['packages']:
            if 'ARTIFACTORY' in package['src_pkg'].encode("ascii"):

                url = package['src_pkg'].encode("ascii").replace('ARTIFACTORY', self.ART_URL)
                src_pkg = url.replace('VERSION', self.version)
                dst_pkg = package['dst_pkg'].encode("ascii")

                try:
                    self.log.info("curl -u {0} -o {1} {2}".format(self.AUTH, dst_pkg, src_pkg))
                    os.system("curl -u {0} -o {1} {2}".format(self.AUTH, dst_pkg, src_pkg))
                except:
                    self.log.error("{0} file downloading is failed".format(src_pkg))
                    sys.exit(1)
            else:
                self._scripts_copy(package['src_pkg'].encode("ascii"), package['dst_pkg'].encode("ascii"))

    def _scripts_copy(self, src, dst):

        try:
            self.log.info('Copy file {0} to {1}'.format(src, dst))
            copyfile(src, dst)
        except:
            self.log.error('file {0} copy filed to destination {1}'.format(src, dst))
            sys.exit(1)

    def _clean_local_artifacts(self):
        """
        generate tar archive for the customer from downloaded versions
        """
        print('running clean_local_artifacts')
        # clean previous versions
        cmd = """rm -rf AWS/EMR/s3_bucket/{0}/artifacts && mkdir -p AWS/EMR/s3_bucket/{0}/artifacts """.format(self.emr_version)
        try:
            os.system(cmd)
        except Exception as err:
            print err
            pass

    def upload_artifacts_to_s3(self):

        self._clean_local_artifacts()
        self._download_pkgs()

        copy_scripts = "aws s3 cp  --recursive ./AWS/EMR/emr_install/{0} {1}/{0}/emr-install/ --acl aws-exec-read".format(self.emr_version,self.s3_bucket)
        copy_artifacts = "aws s3 cp  --recursive ./AWS/EMR/s3_bucket/{0}/artifacts {1}/{0}/artifacts/ --acl aws-exec-read".format(self.emr_version, self.s3_bucket)
        for cmd in copy_scripts, copy_artifacts:
            try:
                self.log.info(cmd)
                os.system(cmd)
            except:
                self.log.error("emr-install scripts upload is failed")
                sys.exit(1)

if __name__=='__main__':
    main()

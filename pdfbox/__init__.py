#!/usr/bin/python3

"""
Python interface to Apache PDFBox.
"""

import hashlib
import html.parser
import os
import pathlib
import re
import shutil
import urllib.request

import appdirs
import pkg_resources
import sarge
from sarge import run, Capture

pdfbox_archive_url = 'https://archive.apache.org/dist/pdfbox/'

class _PDFBoxVersionsParser(html.parser.HTMLParser):
    """
    Class for parsing versions available on PDFBox archive site.
    """

    def feed(self, data):
        self.result = []
        super(_PDFBoxVersionsParser, self).feed(data)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for a in attrs:
                if a[0] == 'href':
                    s = a[1].strip('/')
                    if re.search('\d+\.\d+\.\d+.*', s):
                        self.result.append(s)

class PDFBox(object):
    """
    Python interface to Apache PDFBox.

    Methods
    -------
    extract_text(input_path, output_path='',
                 password=None, encoding=None, html=False, sort=False,
                 ignore_beads=False, start_page=1, end_page=None)
        Extract all text from PDF file.
    """

    def _verify_sha512(self, data, digest):
        """
        Verify SHA512 checksum.
        """

        return hashlib.sha512(data).hexdigest() == digest

    def _get_latest_pdfbox_url(self):
        r = urllib.request.urlopen(pdfbox_archive_url)
        try:
            data = r.read()
        except:
            raise RuntimeError('error retrieving %s' % pdfbox_archive_url)
        else:
            data = data.decode('utf-8')
        p = _PDFBoxVersionsParser()
        p.feed(data)
        latest_version = sorted(p.result, key=pkg_resources.parse_version)[-1]
        return pdfbox_archive_url + latest_version + '/pdfbox-app-' + \
            latest_version + '.jar'

    def _get_pdfbox_path(self):
        """
        Return path to local copy of PDFBox jar file.
        """

        # Use PDFBOX environmental variable if it exists:
        if 'PDFBOX' in os.environ:
            pdfbox_path = pathlib.Path(os.environ['PDFBOX'])
            if not pdfbox_path.exists():
                raise RuntimeError('pdfbox not found')
            return pdfbox_path

        # Use platform-specific cache directory:
        a = appdirs.AppDirs('python-pdfbox')
        cache_dir = pathlib.Path(a.user_cache_dir)

        # Try to find pdfbox-app-*.jar file with most recent version in cache directory:
        file_list = list(cache_dir.glob('pdfbox-app-*.jar'))
        if file_list:
            def f(s):
                v = re.search('pdfbox-app-([\w\.\-]+)\.jar', s.name).group(1)
                return pkg_resources.parse_version(v)
            return sorted(file_list, key=f)[-1]
        else:
            # If no jar files are cached, find the latest version jar, retrieve it, 
            # cache it, and verify its checksum:
            pdfbox_url = self._get_latest_pdfbox_url()
            sha512_url = pdfbox_url + '.sha512'
            r = urllib.request.urlopen(pdfbox_url)
            try:
                data = r.read()
            except:
                raise RuntimeError('error retrieving %s' % pdfbox_url)
            else:
                if not os.path.exists(cache_dir.as_posix()):
                    cache_dir.mkdir(parents=True)
                pdfbox_path = cache_dir.joinpath(pathlib.Path(pdfbox_url).name)
                with open(pdfbox_path.as_posix(), 'wb') as f:
                    f.write(data)

            r = urllib.request.urlopen(sha512_url)
            encoding = r.headers.get_content_charset('utf-8')
            try:
                sha512 = r.read().decode(encoding).strip()
            except:
                raise RuntimeError('error retrieving sha512sum')
            else:
                if not self._verify_sha512(data, sha512):
                    raise RuntimeError('failed to verify sha512sum')

            return pdfbox_path

    def __init__(self):
        self.pdfbox_path = self._get_pdfbox_path()
        self.java_path = shutil.which('java')
        if not self.java_path:
            raise RuntimeError('java not found')

    def extract_text(self, input_path, output_path='',
                     password=None, encoding=None, html=False, sort=False,
                     ignore_beads=False, start_page=1, end_page=None, always_next=False):
        """
        Extract all text from PDF file.

        Parameters
        ----------
        input_path : str
            Input PDF file.
        output_path : str
            Output text file. If not specified, the extracted text is returned.
        password : str
            PDF password.
        encoding : str
            Text file encoding.
        html : bool
            If True, extract as HTML.
        sort : bool
            If True, sort text before returning it.
        ignore_beads : bool
            If True, ignore separation by beads.
        start_page : int
            First page to extract (starting with 1).
        end_page : int
            Last page to extract (starting with 1).

        Returns
        -------
        text : str
            Extracted text. If `output_path` is not specified, nothing is returned.
        """

        options = (' -password {password}'.format(password=password) if password else '') +\
                  (' -encoding {encoding}'.format(encoding=encoding) if encoding else '') +\
                  (' -html' if html else '') +\
                  (' -sort' if sort else '') +\
                  (' -ignoreBeads' if ignore_beads else '') +\
                  (' -startPage {start_page}'.format(start_page=start_page) if start_page else '') +\
                  (' -endPage {end_page}'.format(end_page=end_page) if end_page else '') +\
                  (' -alwaysNext' if always_next else '')
        if not output_path:
            options += ' -console'
        cmd = '{java_path} -jar {pdfbox_path} ExtractText {options} {input_path} {output_path}'.format(java_path=self.java_path,
                                                                                                       pdfbox_path=self.pdfbox_path,
                                                                                                       options=options,
                                                                                                       input_path=input_path,
                                                                                                       output_path=output_path)
        print("PDFBox is running command: ")
        print(cmd)
        p = sarge.capture_both(cmd, async_=True)
        if not output_path:
            return p.stdout.text
        return p

    def split_file(self, input_path, password=None,
                   split=None, start_page=None, end_page=None):
        """
            Split a pdf file.

            Parameters
            ----------
            password : str
                PDF password.
            start_page : int
                The page to start at.
            end_page : int
                The page to stop at.
            split : int
                Number of pages of every splitted part of the pdf.
        """
        options = (' -password {password}'.format(password=password) if password else '') +\
                  (' -startPage {start_page}'.format(start_page=start_page) if start_page else '') +\
                  (' -endPage {end_page}'.format(end_page=end_page) if end_page else '') +\
                  (' -split {split}'.format(split=split) if split else '')
        cmd = '{java_path} -jar {pdfbox_path} PDFSplit {options} {input_path}'.format(java_path=self.java_path,
                                                                                      pdfbox_path=self.pdfbox_path,
                                                                                      options=options,
                                                                                      input_path=input_path)
        self._run_cmd(cmd)

    def merge(self, source_files=[], target_file="merged.pdf"):
        """
            Merge pdf files.

            Parameters
            ----------
            source_files : [str]
                List of file paths to merge.
            target_file : str
                Path of pdf file to merge into. Default will be local directory 'merged.pdf'
        """
        if len(source_files) < 2:
            print("Not enough source files to merge.  Need to have at least 2 source files.")
            return
        cmd = '{java_path} -jar {pdfbox_path} PDFMerger {source} {target}'.format(java_path=self.java_path,
                                                                                pdfbox_path=self.pdfbox_path,
                                                                                source=" ".join(source_files),
                                                                                target=target_file)
        self._run_cmd(cmd)

    def pdf_debugger(self, input_path, password=None, view_structure=None):
        """
            Opens the pdf in a debugger.
        """
        options = (' -password {password}'.format(password=password) if password else '') +\
                (' -viewstructure' if view_structure else '')
        cmd = '{java_path} -jar {pdfbox_path} PDFDebugger {input_path} {options}'.format(java_path=self.java_path,
                                                                                pdfbox_path=self.pdfbox_path,
                                                                                options=options,
                                                                                input_path=input_path)
        self._run_cmd(cmd)

    def to_image(self, input_path, password=None, image_type=None, output_prefix=None,
                start_page=None, end_page=None, page=None, dpi=None, color=None, cropbox=None, time=None):
        """
            Turns each page of a pdf into an individual image with the page number on the end of the file name.
            By default if 'test.pdf' has 2 pages you will get 'test1.jpg' and 'test2.jpg'.

            Supports all the options found on the jar.
            https://pdfbox.apache.org/2.0/commandline.html#pdftoimage
        """
        options = (' -password {password}'.format(password=password) if password else '') +\
            (' -imageType {image_type}'.format(image_type=image_type) if image_type else '') +\
            (' -outputPrefix {output_prefix}'.format(output_prefix=output_prefix) if output_prefix else '') +\
            (' -startPage {start_page}'.format(start_page=start_page) if start_page else '') +\
            (' -endPage {end_page}'.format(end_page=end_page) if end_page else '') +\
            (' -page {page}'.format(page=page) if page else '') +\
            (' -dpi {dpi}'.format(dpi=dpi) if dpi else '') +\
            (' -color {color}'.format(color=color) if color else '') +\
            (' -cropbox {cropbox}'.format(cropbox=" ".join(cropbox)) if cropbox else '') +\
            (' -color {color}'.format(color=color) if color else '')
        cmd = '{java_path} -jar {pdfbox_path} PDFToImage {input_path} {options}'.format(java_path=self.java_path,
                                                                                pdfbox_path=self.pdfbox_path,
                                                                                options=options,
                                                                                input_path=input_path)
        self._run_cmd(cmd)

    def _run_cmd(self, cmd):
        print("PDFBox is running command: ")
        print(cmd)
        p = run(cmd, stdout=Capture(), async_=True)
        p.close()
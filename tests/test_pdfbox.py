#!/usr/bin/env python

from unittest import main, TestCase

import pdfbox
import os
from glob import glob

TEST_FOLDER = 'tests'
RESULTS_FOLDER = 'test_results'
# To generate test PDF, process test.md with pandoc using the command
# pandoc -t latex test.md -o test.pdf
class test_pdfbox(TestCase):
    def test_extract(self):
        p = pdfbox.PDFBox()
        text = p.extract_text(os.path.join(TEST_FOLDER, 'test.pdf'))
        self.assertEqual(text, 'this is a test PDF\n')

    def test_merge(self):
        p = pdfbox.PDFBox()
        p.merge([os.path.join(TEST_FOLDER, 'test.pdf'), os.path.join(TEST_FOLDER, 'test1.pdf')], 
                    target_file=os.path.join(TEST_FOLDER, RESULTS_FOLDER, 'merged.pdf'))
        merged_file = p.extract_text(os.path.join(TEST_FOLDER, RESULTS_FOLDER, 'merged.pdf'))
        self.assertEqual(merged_file, 'this is a test PDF\nthis is a test PDF\n')
    
    def test_split(self):
        p = pdfbox.PDFBox()
        p.split_file(os.path.join(TEST_FOLDER, RESULTS_FOLDER, 'merged.pdf'))
        pdf_files = glob(os.path.join(TEST_FOLDER, RESULTS_FOLDER, '*-*.pdf'))
        self.assertEqual(len(pdf_files), 2)

    def test_image(self):
        p = pdfbox.PDFBox()
        p.merge([os.path.join(TEST_FOLDER, 'test.pdf'), os.path.join(TEST_FOLDER, 'test1.pdf')], 
                    target_file=os.path.join(TEST_FOLDER, RESULTS_FOLDER, 'merged.pdf'))
        p.to_image(os.path.join(TEST_FOLDER, RESULTS_FOLDER, 'merged.pdf'), dpi=24)
        self.assertEqual(len(glob(os.path.join(TEST_FOLDER, RESULTS_FOLDER, '*.jpg'))), 2)


def tearDownModule():
    empty_results()

def setUpModule():
    empty_results()

def empty_results():
    for f in glob(os.path.join(TEST_FOLDER, RESULTS_FOLDER, '*')):
        os.remove(f)
        print("{} removed.".format(f))

if __name__ == '__main__':
    main()

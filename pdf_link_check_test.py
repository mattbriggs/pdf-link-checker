'''Tests for pdf_linker.check.py'''

import pdf_link_check as plc

def test_get_split_large():
    '''Function to split a number into four equal(ish) sections.'''
    number_to_split = 100
    split = plc.get_split(number_to_split)
    
    assert [(0, 25), (26, 50), (51, 75), (76, 100)] == split

def test_get_split_small():
    '''Function to split a number into four equal(ish) sections.'''
    number_to_split = 10
    try:
        split = plc.get_split(number_to_split)
        out_stuff = "Success"
    except Exception as e:
        out_stuff = str(e)

    assert "Number too small to split into four sections." == out_stuff

def test_check_pdf_links_long():
    '''Function to test crawl for a long PDF (under 13 pages)'''
    file_check = plc.check_pdf_links("data\\testpdf.pdf")
    data_check = [3, 'https://en.wikipedia.org/wiki/Fish', 200, 'NA']

    assert data_check == file_check[1]

def test_check_pdf_links_short():
    '''Function to test crawl for a short PDF (under 13 pages)'''
    file_check = plc.check_pdf_links("data\\pdflink.pdf")
    data_check = [1, ' http://www.adobe.com/suportservice/devrelations/PDFS/TN5150.PDFMARK.PDF', 404, 'NA']

    assert data_check == file_check[1]
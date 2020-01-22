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


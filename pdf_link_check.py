''' PDF Link Check
    For more information see: https://github.com/mattbriggs/pdf-link-checker
    PDFLinkCheck.py checks the hyperlinks in an Portable Document Format (PDF)
    file.

    Release V1.0 2020.1.13
'''

import csv
import PyPDF2 as pypdf
import requests
from threading import Thread


def get_split(numtosplit):
    '''Split a number into four equal(ish) sections. Number of pages must be greater than 13.'''
    if numtosplit > 13:
        sections = []
        breaksize = int(numtosplit/4)
        sec1_start = 0
        sec1_end = breaksize
        sec2_start = breaksize + 1
        sec2_end = breaksize * 2
        sec3_start = sec2_end + 1
        sec3_end = breaksize * 3
        sec4_start = sec3_end +1
        sec4_end = numtosplit

        sections = [(sec1_start, sec1_end), (sec2_start, sec2_end ), (sec3_start, sec3_end), (sec4_start, sec4_end)]

        return(sections)

    else:
        raise ValueError("Number too small to split into four sections.")


def get_links_from_page(indexstart, indexend, pdfobject):
    ''' - Extract pages from the PDF using the incoming range.
        - For each page, find annotations, and URIs in the annotations.
            - Get the URIs.
                - For each URI try to make a web request and get the response code.
                - Record the page number, URI, and response code result or NA for timeouts.
    '''

    reportfrag = []
    for i in range[indexstart:indexend]:
        page_obj = pdfobject.getPage(i)
        page_no = i + 1
        annots = page_obj["/Annots"]
        for a in annots:
            u = a.getObject()
            if "/A" in u:
                uris = u["/A"]
                if  "/URI" in uris:
                    raw_url = uris["/URI"]
                    try:
                        x = requests.get(raw_url, timeout=5, stream=True)
                        code = x.status_code
                        x.close()
                        request_error = "NA"
                    except Exception as e:
                        print(e)
                        code = "NA"
                        request_error = str(e)
                    print("{} : {} : {}".format(page_no, raw_url, code))
                    record = [page_no, raw_url, code, request_error]
                    reportfrag.append(record)
    return reportfrag

def main():
    '''Main logic of the script:
    - Get input PDF and output CSV location.
    - Get the number of pages, and split into four equal sections
    - Get the range for each section, and send each section range to the parser running its own thread.
    - Save the report.
    '''

    print("Starting")
    pdf_file = input("Add PDF file > ")
    report_out = input("Save Report (CSV) > ")
    pdf = pypdf.PdfFileReader(pdf_file)
    pages = pdf.numPages
    link_report = [["page", "url", "status", "request-error"]]
    if pages < 13:
        link_report.append(get_links_from_page(0, pages, pdf))
    else:
        split = get_split(pages)
        for i in range(4):
            th = Thread(get_links_from_page, (split[i][0], split[i][1], pdf))
            th.start()

    # Generate CSV output

    print("Done: {}".format(report_out))

    csvout = open(report_out, 'w', newline="")
    csvwrite = csv.writer(csvout)
    for r in link_report:
        csvwrite.writerow(r)
    csvout.close()

if __name__ == "__main__":
    main()

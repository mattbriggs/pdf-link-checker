''' PDF Link Check
    For more information see: https://github.com/mattbriggs/pdf-link-checker
    PDFLinkCheck.py checks the hyperlinks in an Portable Document Format (PDF)
    file.
'''

import csv
import PyPDF2 as pypdf
import requests


def main():
    '''Main logic of the script:
    - Get input PDF and output CSV location.
    - Extract pages from the PDF.
    - For each page, find annotations, and URIs in the annotations.
        - Get the URIs.
            - For each URI try to make a web request and get the response code.
            - Record the page number, URI, and response code result or NA for timeouts.
    - Save the report.
    '''

    print("Starting")
    pdf_file = input("Add PDF file > ")
    report_out = input("Save Report (CSV) > ")
    pdf = pypdf.PdfFileReader(pdf_file)
    pages = pdf.numPages

    link_report = [["page", "url", "status", "request-error"]]

    for i in range(pages):
        page_obj = pdf.getPage(i)
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
                    link_report.append(record)

    # Generate CSV output

    print("Done: {}".format(report_out))

    csvout = open(report_out, 'w', newline="")
    csvwrite = csv.writer(csvout)
    for r in link_report:
        csvwrite.writerow(r)
    csvout.close()

if __name__ == "__main__":
    main()

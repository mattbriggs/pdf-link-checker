# PDF Link Check (Python script)

`pdf_link_check.py` checks the hyperlinks in an Portable Document Format (PDF) file. The script is a command line app.

## Install dependencies

The script requires the following dependencies:

- [Python 3.6 or greater](https://www.python.org/downloads/).
- Python module: PyPDF2.

    Install with PIP: `pip install PyPDF2`

    For more information, see [pypi.org](https://pypi.org/project/PyPDF2/).

- Python module: Requests

    Install with PIP: `pip install requests`.

    For more information, see [pypi.org](https://pypi.org/project/requests/).

- Python module: CSV

    Part of the Python core packages. No need to install with PIP.

    For more information, see [CSV File Reading and Writing](https://docs.python.org/3/library/csv.html)


## Use `PDFLinkCheck.py`

Run PDFLinkChecker from your command line:

1. Open your command line and run: `python <path to script>/pdf_link_check.py`
2. The script will ask for the path of the PDF you would like to parse. Enter the absolute path name.<br>On a Windows 10 machine, this might look like: `c:\<pathtoyourpdf>/pdffile.pdf`
3. The script will ask for a location and filename where you would like to save the output.<br>On a Windows 10 machine, this might look like: `c:\<pathtoyourreport>/pdflinkreport.csv`
4. The script will run. The script displays in the terminal:
    - PDF page number
    - URI checked
    - Response code. You can find more information about response codes at [List of HTTP status codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes).

    The script will produce an "NA" rather than a response code for URIs that timeout after five seconds. The script will display the capture and display the error code in the terminal.

5. When the script is done, it saves the result to the pathname an filename that you indicated.
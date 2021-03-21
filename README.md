# PDF Link Check (Python script)

`pdf_link_check.py` checks the hyperlinks in a Portable Document Format (PDF) file. The script is a command line app.

Release: V1.1.1 2020.1.23


## Install dependencies

You can either install the dependencies for this script by using PIP and the requirements file or installing each individual dependent module.

### To use Pip

1. Navigate your CLI to the folder containing the repository with the `requirements.txt` file.
2. Run the following command:
    ```bash
    pip install -r requirements.txt
    ```

### Install individual modules

The script requires the following dependencies:

- [Python 3.6 or greater](https://www.python.org/downloads/).
- Python module: PyPDF2.

    Install with PIP: `pip install PyPDF2`

    For more information, see [pypi.org](https://pypi.org/project/PyPDF2/).

- Python module: Requests

    Install with PIP: `pip install requests`.

    For more information, see [pypi.org](https://pypi.org/project/requests/).

- Python module: CSV

    Part of the Python core packages. No need to install with PIP. CSV stands for comma separated value.

    For more information, see [CSV File Reading and Writing](https://docs.python.org/3/library/csv.html)

- Python module: operator

    Part of the Python core packages. No need to install with PIP.

    For more information, see [operator](https://docs.python.org/3/library/operator.html#module-operator)

- Python module: Threading

    Part of the Python core packages. No need to install with PIP.

    For more information, see [threading — Thread-based parallelism](https://docs.python.org/3.6/library/threading.html)


## Use `pdf_link_check.py`

Run `pdf_link_check.py` from your command line:

1. Open your command line and run: `python <path to script>/pdf_link_check.py`
2. The script will ask for the path of the PDF you would like to parse. Enter the absolute path name.<br>On a Windows 10 machine, this might look like: `c:\<pathtoyourpdf>/pdffile.pdf`
3. The script will ask for a location and filename where you would like to save the output.<br>On a Windows 10 machine, this might look like: `c:\<pathtoyourreport>/pdflinkreport.csv`
4. The script will run. The script displays in the terminal:
    - PDF page number
    - URI checked
    - Response code. You can find more information about response codes at [List of HTTP status codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes).
    - Error information for requests that fail. These are the exceptions raised by the **[Requests module](https://2.python-requests.org/en/master/)**. 

    The script will produce an "NA" rather than a response code for URIs that timeout after five seconds. The script will display the capture and display the error code in the terminal.

5. When the script is done, it saves the result to the pathname that you indicated. You can open the CSV in Microsoft Excel.

## Run Pytest to validate returns

From the script directory, run `pytest` to validate the code. The tests use the PDFs in the **data** folder.

import os
from subprocess import Popen, PIPE
from shutil import rmtree
from tempfile import mkdtemp


def pdflatex(latex):
    latex = latex.encode('utf-8')
    try:
        directory = mkdtemp()
        jobname = 'output'
        filename = os.path.join(directory, jobname) + '.pdf'
        for _ in range(3):
            with open(os.devnull, 'wb') as devnull:
                if os.name == 'nt':
                    process = Popen(['pdflatex',
                                     '--output-directory=%s' % directory,
                                     '--job-name=%s' % jobname],
                                    stdin=PIPE, stdout=devnull, stderr=PIPE)
                else:
                    process = Popen(['pdflatex',
                                     '-output-directory', directory,
                                     '-jobname', jobname],
                                    stdin=PIPE, stdout=devnull, stderr=PIPE)
            _stdout, stderr = process.communicate(latex)
        try:
            with open(filename, 'rb') as f:
                pdf = f.read()
        except IOError:
            if stderr:
                raise OSError(stderr)
            else:
                raise
    finally:
        rmtree(directory)
    return pdf

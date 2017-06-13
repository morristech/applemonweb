import os
from subprocess import Popen, PIPE
from shutil import rmtree
from tempfile import mkdtemp
from urllib.parse import quote

from django.http import HttpResponse
from django.template.loader import render_to_string


def render_latex(request, template, dictionary, filename):
    latex = render_to_string(template, dictionary)
    pdf = pdflatex(latex)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(
        quote(filename)
    )
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response


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

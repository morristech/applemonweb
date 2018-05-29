import io
import datetime
import os
import subprocess
import tempfile

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Table
)


title = "Sound Level Monitoring Report"
author = "Applemon"
thresholds = [85, 100]


def parse_timestamp(d):
    return datetime.datetime.strptime(d, '%d-%m-%Y,%H:%M:%S')


def to_decibels(x):
    """Convert pressure ratio squared to decibels."""
    return 10. * np.log10(x)


def to_ratio(x):
    """Convert decibels to pressure ratio squared."""
    return 10**(x / 10.)


def generate_noise_report(files):
    sound_logs = []
    other_pdfs = []
    for uploaded_file in files:
        if uploaded_file.content_type == 'text/plain':
            sound_logs.append(uploaded_file.temporary_file_path())
        elif uploaded_file.content_type == 'application/pdf':
            other_pdfs.append(uploaded_file.temporary_file_path())
        else:
            raise Exception("File type {} is not text or PDF.".format(
                uploaded_file.content_type
            ))
    assert sound_logs, "No sound level data logs provided."
    (_fh1, report_filename) = tempfile.mkstemp(suffix='.pdf')
    (_fh2, assembled_filename) = tempfile.mkstemp(suffix='.pdf')
    try:
        doc = SimpleDocTemplate(report_filename, pagesize=letter)
        doc.title = title
        doc.author = author
        styles = getSampleStyleSheet()
        max_date = None
        story = []

        for filename in sound_logs:
            assert open(filename).readline().strip() == \
                'STANDARD HD600 DATA LOGGER SamplingRate:1.0;', \
                "Sound data logs must use HD600 format with 1-second samples."
            df = pd.read_csv(filename, sep=', ', header=None, skiprows=1,
                             names=['timestamp', 'level', 'unit'],
                             parse_dates=['timestamp'],
                             date_parser=parse_timestamp, engine='python')
            date = df['timestamp'].max().date()
            if not max_date or date > max_date:
                max_date = date
            unit = df['unit'].iloc[0]
            assert unit in ['dBA', 'dBC'], \
                "Sound must be measured in A/C-weighted decibels (dBA or dBC)."
            assert df['unit'].eq(unit).all(), \
                "Sound level units must be consistent."
            df['ratio'] = df['level'].apply(to_ratio)
            leq_fmt = "{overall:.1f} {dB} (over entire session)"
            if len(df) > 3600:
                leq_fmt += "\n{min:.1f} {dB} - {max:.1f} {dB} (rolling 1-hour)"
                df['leq'] = to_decibels(
                    df['ratio'].rolling(3600, center=True).mean()
                )
                df['leq'].fillna(method='bfill', inplace=True)
                df['leq'].fillna(method='ffill', inplace=True)
            else:
                df['leq'] = to_decibels(df['ratio'].mean())
            leq = leq_fmt.format(
                overall=to_decibels(df['ratio'].mean()),
                dB=unit,
                min=df['leq'].min(), max=df['leq'].max(),
            )
            story.append(Paragraph("Sound Level Monitoring Report",
                         styles["Title"]))
            story.append(Paragraph("Session Summary", styles["Heading2"]))
            story.append(Table([
                ['Start Time', df['timestamp'].iloc[0]],
                ['Stop Time', df['timestamp'].iloc[-1]],
                ['Duration', str(
                    df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
                ).replace('0 days ', '')],
                ['Device', 'HD600'],
                ['Lmin', '{} {}'.format(df['level'].min(), unit)],
                ['Lmax', '{} {}'.format(df['level'].max(), unit)],
                ['Leq', leq],
            ]))

            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(1, 1, 1)
            ax.set_title("Logged Data")
            ax.set_xlabel("Time")
            ax.set_ylabel(unit)
            ax.grid(True)
            (line,) = ax.plot_date(df['timestamp'], df['level'], fmt='b-',
                                   linewidth=0.5)
            line.set_label("L")
            (line2,) = ax.plot_date(df['timestamp'], df['leq'], fmt='g-',
                                    linewidth=5, alpha=0.7)
            line2.set_label("Leq")
            for threshold in thresholds:
                ax.axhline(threshold, color='r', linestyle='--', alpha=0)
            ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            ax.legend(loc='upper right', framealpha=0)

            fig.autofmt_xdate()
            buf = io.BytesIO()
            FigureCanvasAgg(fig).print_figure(buf, format='png')
            story.append(Image(buf))

            story.append(PageBreak())

        doc.build(story)
        subprocess.check_call([
            'gs', '-dSAFER', '-dBATCH', '-dNOPAUSE', '-dQUIET',
            '-sDEVICE=pdfwrite', '-dPDFSETTINGS=/ebook',
            '-sPAPERSIZE=letter', '-dFIXEDMEDIA', '-dPDFFitPage',
            '-sOutputFile={}'.format(assembled_filename)
        ] + other_pdfs + [report_filename])
        with open(assembled_filename, 'rb') as f:
            pdf = f.read()
    finally:
        os.remove(report_filename)
        os.remove(assembled_filename)
    if max_date:
        filename = 'noise_{}.pdf'.format(max_date)
    else:
        filename = 'noise.pdf'
    return (pdf, filename)

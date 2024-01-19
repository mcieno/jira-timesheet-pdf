#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import calendar
import datetime
import json
import logging
import os
import sys
import textwrap

import jira
import reportlab, reportlab.platypus

JIRA_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


def generate_report(
    output: str,
    title: str,
    date_from: datetime.date,
    date_to: datetime.date,
    worklogs_by_issue: dict[jira.resources.Issue, list[jira.resources.Worklog]],
) -> reportlab.platypus.doctemplate.BaseDocTemplate:
    doc = reportlab.platypus.SimpleDocTemplate(
        output,
        pagesize=reportlab.lib.pagesizes.landscape(reportlab.lib.pagesizes.A4),
    )

    stylesheet = reportlab.lib.styles.getSampleStyleSheet()

    elements = []

    elements.append(
        reportlab.platypus.Paragraph(
            title,
            reportlab.lib.styles.ParagraphStyle(
                '',
                parent=stylesheet['Heading2'],
                alignment=reportlab.lib.enums.TA_CENTER,
            ),
        )
    )

    style = [
        # Grid border
        ('GRID',   (+0, +0), (-1, -1), 0.2, reportlab.lib.colors.lightgrey),
        # Horizontally center everything
        ('ALIGN',  (+0, +0), (-1, -1), 'CENTER'),
        # Vertically center everything
        ('VALIGN', (+0, +0), (-1, -1), 'MIDDLE'),
        # Primary font
        ('FONT',   (+0, +0), (-1, -1), 'Helvetica', 8, 8),
        # Make first column (issue descriptions) bold and left-aligned
        ('ALIGN',  (+0, +0), (+0, -1), 'LEFT'),
        ('FONT',   (+0, +0), (+0, -1), 'Helvetica-Bold', 8, 8),
        # Make first row (days) bold
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8, 8),
    ]

    data = [
        ['', ],
        # ['Issue 1', ],
        # ['Issue 2', ],
        # ...
    ]

    for day in range((date_to - date_from).days + 1):
        current_date = (date_from + datetime.timedelta(days=day))
        if current_date.weekday() >= 5:
            style.append(
                # Darker weekend background color
                ('BACKGROUND', (day+1, +0), (day+1, -1), reportlab.lib.colors.whitesmoke),
            )

        data[0].append(
            current_date.strftime("%d") + "\n" + current_date.strftime("%a")[0]
        )

    for issue, worklogs in worklogs_by_issue.items():
        data.append([textwrap.fill(f'{issue.key} - {issue.fields.summary}', 50), ])

        for day in range((date_to - date_from).days + 1):
            current_date = (date_from + datetime.timedelta(days=day))
            if current_date.weekday() >= 5:
                style.append(
                    # Darker weekend background color
                    ('BACKGROUND', (day+1, +0), (day+1, -1), reportlab.lib.colors.whitesmoke),
                )

            time_spent_seconds = sum(
                worklog.timeSpentSeconds
                for worklog in worklogs
                if datetime.datetime.strptime(worklog.started, JIRA_DATETIME_FORMAT).date() == current_date
            )

            data[-1].append(
                f'{time_spent_seconds / 3600:.1f}' if time_spent_seconds > 0 else ''
            )

    elements.append(
        reportlab.platypus.Table(
            data,
            style=style,
            colWidths=[None] + [6*reportlab.lib.pagesizes.mm] * (len(data[0]) - 1),
        )
    )

    total_spent_seconds = sum(
        sum(worklog.timeSpentSeconds for worklog in worklogs)
        for worklogs in worklogs_by_issue.values()
    )

    elements.append(
        reportlab.platypus.Paragraph(
            f'Total Hours: {total_spent_seconds / 3600:.2f}',
            reportlab.lib.styles.ParagraphStyle(
                '',
                parent=stylesheet['BodyText'],
                alignment=reportlab.lib.enums.TA_CENTER,
            ),
        )
    )

    doc.build(elements)

    return doc


def get_worklogs_by_issue(
    client: jira.JIRA,
    user: str,
    date_from: datetime.date,
    date_to: datetime.date,
) -> dict[jira.resources.Issue, list[jira.resources.Worklog]]:
    issues = client.search_issues(f'''
        worklogAuthor = '%s'
        AND worklogDate >= {json.dumps(date_from.strftime('%Y-%m-%d'))}
        AND worklogDate <= {json.dumps(date_to.strftime('%Y-%m-%d'))}
        ORDER BY created ASC
    ''' % user.replace("'", r"\'"))

    logging.info(f'Found {len(issues)} issues')

    worklogs_by_issue: dict[jira.resources.Issue, list[jira.resources.Worklog]] = {}

    for issue in issues:
        worklogs = client.worklogs(issue.key)
        logging.info(f'Issue {issue}: found {len(worklogs)} worklogs')

        worklogs = list(filter(
            lambda worklog: worklog.author.displayName == user,
            worklogs,
        ))
        logging.info(f'Issue {issue}: found {len(worklogs)} worklogs by user {user}')

        worklogs = list(filter(
            lambda worklog: date_from <= datetime.datetime.strptime(worklog.started, JIRA_DATETIME_FORMAT).date() <= date_to,
            worklogs,
        ))
        logging.info(f'Issue {issue}: found {len(worklogs)} worklogs in date range {date_from} - {date_to}')

        worklogs_by_issue[issue] = worklogs

    return worklogs_by_issue


def main(args) -> None:
    yyyy_mm = datetime.datetime.strptime(args.yyyy_mm, '%Y-%m')
    year, month = yyyy_mm.year, yyyy_mm.month
    month_start = datetime.date(year, month, 1)
    month_last = datetime.date(year, month, calendar.monthrange(year, month)[1])

    logging.info(f'Generating worklog report from {month_start} to {month_last} for user {args.user}')

    worklogs_by_issue = get_worklogs_by_issue(
        jira.JIRA(f'https://{args.server}', basic_auth=(args.auth_email, args.auth_token)),
        args.user,
        month_start,
        month_last,
    )

    generate_report(
        args.output or month_start.strftime('timesheet-%Y-%m.pdf'),
        month_start.strftime('%B %Y'),
        month_start,
        month_last,
        worklogs_by_issue,
    )



if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--server',
        type=str,
        required=True,
        help='The Jira server domain name; e.g. example.atlassian.net',
    )
    parser.add_argument(
        '--auth-email',
        type=str,
        required=True,
        help='The email for authenticating to the Jira API',
    )
    parser.add_argument(
        '--auth-token',
        type=str,
        default=os.environ.get('AUTH_TOKEN'),
        help='The token for authenticating to the Jira API (defaults to AUTH_TOKEN environment variable)',
    )
    parser.add_argument(
        '--yyyy-mm',
        type=str,
        default=datetime.datetime.now().strftime('%Y-%m'),
        help='The YYYY-MM formatted month for which to generate the report (defaults to current month)',
    )
    parser.add_argument(
        '--user',
        type=str,
        required=True,
        help='The display name of the user for which to generate the report; e.g. John Doe',
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='The file name where to output the report (defaults to timesheet-YYYY-MM.pdf)',
    )

    args = parser.parse_args()

    main(args)

# syntax=docker/dockerfile:1
FROM python:3.12

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install -r /tmp/requirements.txt

COPY jira-timesheet-pdf /

ENTRYPOINT ["/jira-timesheet-pdf"]
CMD ["--help"]

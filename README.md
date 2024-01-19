# Jira Timesheet PDF

Simple script to generate monthly timesheets based on Jira's worklog.

Adapted from [jordanjambazov/jira-timesheet-pdf](https://github.com/jordanjambazov/jira-timesheet-pdf).

## Usage

First things first, you'll need an API token to fetch worklogs from Jira.
Hence, browse to https://id.atlassian.com/manage-profile/security/api-tokens,
create one and paste it to a `.env` (copied from `.env.example`):

```env
AUTH_TOKEN=...
```

That's it... Just run it...

### Build image

```sh
docker build -t jira-timesheet-pdf .

# Have a look at the help
docker run --rm jira-timesheet-pdf --help
```

### Just run it

You'll need a bit of docker volumes kung-fu, otherwise the PDF will be lost with
the container:

```sh
docker run --rm --env-file=.env -v "$(pwd):/app" -w /app -u $(id -u):$(id -g) jira-timesheet-pdf \
    --server=example.atlassian.net \
    --auth-email=user@example.com \
    --user='John Doe' \
    --yyyy-mm 2024-01
```

If you don't like docker volumes kung-fu, consider stdout kung-fu:

```sh
docker run --rm --env-file=.env jira-timesheet-pdf \
    --output=/dev/stdout \
    --server=example.atlassian.net \
    --auth-email=user@example.com \
    --user='John Doe' \
    --yyyy-mm 2024-01 \
    > timesheet.pdf
```

### Example output

<p align="center">
  <img
    width="1185"
    alt="Example timesheet"
    src="https://github.com/mcieno/jira-timesheet-pdf/assets/30049418/af2fa171-bc17-4b7c-8d28-03a13c8dbf5b"
    />
</p>

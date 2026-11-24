# Fictional support sample data

Ternwick Circuit Supply is an invented retailer of everyday electronics and accessories. Its sample conversations give developers repeatable data for API exploration, frontend work, and later classification and response-generation exercises. Names, products, and order references are fictional. Customer email addresses use the reserved `example.com` domain.

The dataset contains **8 customers, 18 conversations, and 53 messages**. Conversation statuses include 6 open, 4 pending, 5 resolved, and 3 closed. The two single-message tickets are open and awaiting a first reply. Resolved conversations end with an agent response. Pending conversations have an outstanding request for information.

## Scenario coverage

Category, sentiment, and urgency describe the author's intent at the scenario level. The metadata lives in the source definitions. The command writes customers, conversations, and messages only.

| Category | Conversations | Messages | Example | Intended sentiment | Intended urgency |
| --- | ---: | ---: | --- | --- | --- |
| Shipping | 3 | 10 | Headphone tracking stalls before a trip | Positive, negative | Normal, high |
| Refund | 3 | 8 | A defective charger return awaits a refund | Positive, neutral, negative | Normal |
| Billing | 3 | 10 | Two entries appear for one order | Positive, neutral, negative | Normal, high |
| Product | 3 | 7 | A customer asks whether a keyboard works with Linux | Neutral | Low, high |
| Account | 2 | 7 | A login loop blocks confirmation before a collection deadline | Positive, negative | Low, high |
| General | 2 | 5 | A customer asks about weekend support hours | Positive, neutral | Low |
| Other | 2 | 6 | A repair club asks to collect empty display cartons | Neutral | Low |

Four cases involve concrete deadlines. They cover a shipment needed before a trip, an invoice before an expense cutoff, a display adapter before a workshop, and account access before the collection desk closes. The texts use those circumstances to convey urgency. See the [authored definitions](../../backend/support/seed_data/scenarios.py).

## Preview and seed

Start local PostgreSQL, load the database variables in the current shell, set `DJANGO_ENV=development`, and apply migrations. Use the backend virtual environment. On macOS or Linux, use `python` from the activated virtual environment for the same commands. See the [setup guide](setup.md#populate-the-development-database).

```powershell
.\.venv\Scripts\python.exe manage.py seed_support_data --dry-run
.\.venv\Scripts\python.exe manage.py seed_support_data
.\.venv\Scripts\python.exe manage.py seed_support_data
```

The preview reports the number of rows it would create and the number it can reuse. In an empty database, the first seed creates all 79 rows. The second creates zero and reuses all 79. The report omits customer details and message text.

## Inspect through the API

Start Django and sign in as a Support Agent or Support Manager using the [local session setup](setup.md#inspect-the-api-locally). In the same PowerShell session, use the cookie jar from the login walkthrough.

```powershell
$samplePage = Invoke-RestMethod "$api/conversations/?status=open&page_size=5" -WebSession $apiSession
$samplePage.results | Select-Object id, subject, status
```

The list can also include other local records. To find a specific seeded conversation, retrieve its UUID from its scenario key in the Django shell, then request that conversation and its timeline.

```powershell
$sampleId = .\.venv\Scripts\python.exe manage.py shell -c "from support.seed_data.inventory import seed_id; print(seed_id('conversation', 'shipping-tracking'))"
$sampleTicket = ($sampleId | Select-Object -Last 1).Trim()
Invoke-RestMethod "$api/conversations/$sampleTicket/" -WebSession $apiSession
Invoke-RestMethod "$api/conversations/$sampleTicket/messages/" -WebSession $apiSession
```

## Clean up

Preview the exact inventory cleanup before running it.

```powershell
.\.venv\Scripts\python.exe manage.py seed_support_data --clear --dry-run
.\.venv\Scripts\python.exe manage.py seed_support_data --clear
```

`--clear` is the explicit destructive action. The command checks every expected UUID against the inventory and validates all fields on every matching row, including parent IDs and timestamps. Missing rows are harmless. Cleanup refuses the entire operation if a matching row changed or if an unrelated conversation, message, analysis, or draft references a sample parent. The command locks matching rows for mutations, deletes exact IDs in child-first order, and checks the actual deletion counts. A failure rolls back the transaction. Repeating cleanup after a successful removal reports zero deletions.

## Identity, timestamps, and safety

The management command uses Django's `BaseCommand` to parse flags, validate the environment, and report results. A fixed UUID5 namespace and stable keys identify each customer and conversation. A message key combines its scenario key and position in the timeline. A matching UUID and exact data mean the command can reuse a row. A different row with the same UUID, or a different customer using the same sample email, causes seed to refuse. A seed pass adds only missing rows.

The timeline starts on November 2, 2026 at 09:00 UTC. Each scenario starts one day after the previous one, and authored minute offsets order its messages. After a validated insert, the command sets the expected timestamps using `QuerySet.update()` on that exact UUID. This works with Django's automatic timestamp fields and keeps timestamps reproducible. All inserts and timestamp updates share one `transaction.atomic()` block. For example, a failed message insert rolls back the earlier customer and conversation inserts as well.

Use the command with `config.settings`, `DJANGO_ENV=development`, and PostgreSQL configured on `127.0.0.1`. The PostgreSQL test settings may use it on the reserved pytest database. The command checks the configured target before opening it and verifies the connected host address and database name before reading sample rows. Production and unknown modes are refused, including previews. Use a local development database for this workflow. A loopback address alone cannot distinguish a local server from a tunnel.

Seed rows persist for manual exploration across sessions. Test fixtures are disposable and normally created within an isolated test database for a specific assertion. Treat the published keys, data, and ordering as a versioned inventory. Preview and clear an unmodified old version before changing its definitions in a local database. Authentic discussion text gives future AI work useful inputs. Scenario metadata is authored context and will need its own review before use as evaluation labels. See the [seed test guide](testing.md#sample-data-tests).

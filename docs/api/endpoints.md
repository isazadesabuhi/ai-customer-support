# API endpoints

All five routes require an authenticated Django staff account (`is_staff=True`). With the current DRF authentication order, Session Authentication followed by Basic Authentication, both anonymous and non-staff requests receive HTTP 403. Session-authenticated POST requests also require a CSRF token. Use Basic Authentication for local inspection over the loopback interface. See the [local API setup](../development/setup.md#inspect-the-api-locally).

This interim policy gives staff access to the single company's support records. Detail and message routes check permissions on the conversation. Permission checks precede UUID resolution, so a denied caller cannot determine whether a conversation exists. Successful and error responses include `Cache-Control: ... private, no-store` directives. TASK-005 will introduce formal authentication and authorization.

## Shared conventions

- Paths have trailing slashes. Identifiers are UUID strings and timestamps use ISO 8601 UTC.
- POST requests take a JSON object with `Content-Type: application/json`. Missing required fields, extra fields, non-string values, invalid field values, and attempts to supply server-owned fields receive 400. Rejected requests leave records unchanged.
- List responses contain `count` (total matching records), `next` and `previous` (URL or `null`), and `results` (an array). `page` defaults to 1 and must be a positive integer. `page_size` defaults to 20 and accepts 1–100 inclusive. Invalid, repeated, or out-of-range pagination parameters receive 400.
- Validation responses map public field names to arrays of messages, for example `{"page_size":["Provide one integer from 1 to 100."]}`. A body that is valid JSON but has the wrong shape uses `non_field_errors`. Malformed JSON and other HTTP errors use `detail`.
- Missing or malformed conversation UUIDs receive 404 with `{"detail":"Not found."}` for authorized users. Unsupported methods receive 405 and unsupported request media types receive 415. Unexpected API errors receive 500 with a generic `detail` message.

## List conversations

`GET /api/conversations/` returns 200 with a paginated list for staff. `status` is optional and accepts one of `open`, `pending`, `resolved`, or `closed`. Invalid or repeated values receive 400. Ordering is newest first by `created_at`, then descending by `id`. There is no request body.

```http
GET /api/conversations/?status=open&page=1&page_size=20 HTTP/1.1
Accept: application/json
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "27a8754e-3156-46c9-b205-21e18fe8a42a",
      "subject": "Order delivery issue",
      "status": "open",
      "customer": {
        "id": "8725e411-b684-49a2-82bf-c6f8228d5cd2",
        "name": "Jane Doe",
        "email": "jane@example.test"
      },
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

The conversation schema is one entry from `results` above. Its read-only `customer` object is limited to `id`, `name`, and `email`. Message history is available through the message list. AI analyses and drafts are private to the data layer.

## Create a conversation

`POST /api/conversations/` creates a conversation for an existing customer. It has no query parameters and returns 201 with the conversation schema above. The model supplies the `open` status, UUID, and timestamps. `customer_id` must be a valid UUID for an existing customer. `subject` must be a string of up to 255 characters with at least one non-whitespace character. A nonexistent customer, invalid subject, or attempt to assign `status`, timestamps, UUID, or nested customer data receives 400.

```http
POST /api/conversations/ HTTP/1.1
Content-Type: application/json

{"customer_id":"8725e411-b684-49a2-82bf-c6f8228d5cd2","subject":"Order delivery issue"}
```

## Retrieve a conversation

`GET /api/conversations/{id}/` returns 200 with the conversation schema above. It takes the UUID from the path and has no body or query parameters. A malformed or unknown UUID receives 404. The response contains only conversation fields and the customer summary.

```http
GET /api/conversations/27a8754e-3156-46c9-b205-21e18fe8a42a/ HTTP/1.1
Accept: application/json
```

## List messages

`GET /api/conversations/{id}/messages/` returns 200 with paginated messages for the authorized parent conversation. It accepts `page` and `page_size`, with no request body. Messages are ordered by `created_at`, then `id`, both ascending. The stored sender values are `customer`, `agent`, and `system`. Each message contains only `id`, `sender`, `content`, and `created_at`. A malformed or unknown parent UUID receives 404.

```http
GET /api/conversations/27a8754e-3156-46c9-b205-21e18fe8a42a/messages/?page_size=2 HTTP/1.1
Accept: application/json
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "fc06adbd-2998-4734-a739-1868fd55d0f6",
      "sender": "customer",
      "content": "My order has not arrived.",
      "created_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

## Create a message

`POST /api/conversations/{id}/messages/` adds an agent message to the conversation in the URL. It takes no query parameters and returns 201 with the message schema. The current conversation status stays the same. `sender` must be `agent`. `content` must be a string of up to 10,000 characters with at least one non-whitespace character. Valid message text keeps its whitespace. Customer and system senders, invalid content, and attempts to write parent, ID, or timestamp fields receive 400. A malformed or unknown parent UUID receives 404.

```http
POST /api/conversations/27a8754e-3156-46c9-b205-21e18fe8a42a/messages/ HTTP/1.1
Content-Type: application/json

{"sender":"agent","content":"Could you provide your order number?"}
```

```json
{
  "id": "131906cc-02bf-4cf6-88c0-e4d9dc4527f6",
  "sender": "agent",
  "content": "Could you provide your order number?",
  "created_at": "2026-01-01T10:05:00Z"
}
```

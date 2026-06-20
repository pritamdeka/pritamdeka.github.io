# Website analytics reference

The site uses privacy-conscious Umami events. Event payloads must never include
search queries, chatbot messages, contact-form contents, email addresses, or
other visitor-provided personal data.

## Event dictionary

| Event | Properties | Purpose |
| --- | --- | --- |
| `theme_change` | `theme`, `source`, `page` | Theme preference and control used |
| `search_open` / `search_close` | `source`, `page` | Search adoption |
| `search_results` | `length_bucket`, `result_count`, `page` | Search usefulness without recording queries |
| `search_result_select` | `destination_type`, `destination_kind`, `page` | Search conversion |
| `chat_open` / `chat_close` | `source`, `page` | Chat engagement |
| `chat_question` | `source`, `length_bucket`, `page` | Question activity without message text |
| `chat_quick_reply` | `category`, `page` | Quick-reply usage |
| `chat_response` | `outcome`, `latency_bucket`, `page` | Chat reliability and perceived speed |
| `cv_download` | `source`, `page` | CV conversion |
| `content_link_open` | `content_type`, `label`, `page` | Publication/project engagement |
| `contact_form_submit` | `outcome`, `page` | Contact conversion and failures |
| `primary_cta` | `action`, `destination`, `page` | Main call-to-action engagement |
| `command_palette_open` | `page` | Command-palette discovery |
| `command_action` | `group`, `action`, `page` | Commands visitors use |

## Recommended Umami goals and boards

- Goal: `cv_download`.
- Goal: `contact_form_submit` filtered to `outcome = success`.
- Funnel: homepage pageview → `content_link_open` → successful contact form.
- Journey: `chat_open` → `chat_question` → `chat_response` with `outcome = success`.
- Journey: `search_open` → `search_results` → `search_result_select`.
- Board: conversions (`cv_download`, successful contact, primary CTAs).
- Board: discovery (search and command-palette events).
- Board: chatbot health (opens, questions, outcomes, and latency buckets).

Review trends after four to six weeks before making major navigation or design
changes. Low-volume data should be treated directionally rather than as a
statistically reliable conclusion.

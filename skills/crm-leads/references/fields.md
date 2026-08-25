# Lead fields and risk levels

| Field | Required | Risk | If missing |
|---|---|---|---|
| company | yes | HIGH | Ask; refuse to create without it |
| contact | no | HIGH | Leave empty, note in receipt |
| title | no | LOW | Leave empty |
| stage | yes | LOW | May be inferred from context; visible in receipt |
| value_cny | no | HIGH | Only explicit amounts; "around/roughly" → ask |
| next_action | no | MED | Leave empty |
| next_due | no | HIGH | Resolve to a concrete date, echo back to confirm |

Stages: `new → contacted → qualified → proposal → won / lost`

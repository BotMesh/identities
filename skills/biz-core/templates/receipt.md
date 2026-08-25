# Receipt template

Every write operation MUST be confirmed with this three-part receipt.

```
✅ Recorded
   <object type + id> · <field: value, one per line>

🔗 Linked
   <related objects created/updated; omit this section if none>

❓ To confirm
   <low-confidence fields as questions; omit this section if none>
```

Rules:
- If the input came from voice, append the transcript in a quoted block so the
  user can correct mishearings.
- The receipt is not a summary — every stored field must appear verbatim.

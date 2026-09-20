# Setup Framework — Docs

How Optima Payment adds custom fields and property setters to other apps' doctypes, and how it
keeps them up to date without overwriting what a client changed in Customize Form.

| Document | What it covers |
|----------|----------------|
| [architecture.md](architecture.md) | The ownership model, install / migrate / uninstall paths, module map, what the sync decides |
| [questions-and-answers.md](questions-and-answers.md) | Short answers: keys and flags, client edits, `field_order`, what uninstall keeps, reading the report |
| [how-to-add-a-feature.md](how-to-add-a-feature.md) | A new group of custom fields and property setters |
| [how-to-alter-a-feature.md](how-to-alter-a-feature.md) | Adding, changing, renaming or removing a field or setter |
| [how-to-write-a-patch.md](how-to-write-a-patch.md) | The one-patch-per-change workflow, with the rename and removal patterns |
| [how-to-check-a-migrate.md](how-to-check-a-migrate.md) | Snapshot the forms before a migrate and compare after |
| [permissions.md](permissions.md) | The two Optima roles and the Custom DocPerm grid |

**Start here if you are new:** the ownership model in
[architecture.md](architecture.md#the-ownership-model), then the Q&A.

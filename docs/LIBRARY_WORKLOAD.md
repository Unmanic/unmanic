# Library workload query and idle notification

Use this query to decide when to update an aggregate media index, refresh a
catalogue, or perform another action after Library work has drained.

`POST /unmanic/api/v2/pending/library/workload` accepts
`{"library_ids": [1, 2]}`. Omit `library_ids`, or pass an empty list, to select
all configured Libraries. Unknown IDs and invalid values return HTTP 400.

The response contains `scan_state`, aggregate `idle`, and a `libraries` list.
Each Library has `library_id`, `tasks` counts keyed by `creating`, `pending`,
`in_progress` and `processed`, `outstanding_tasks`, and `idle`.
A Library is idle only when the scanner is idle and its outstanding count is
zero. Scan state applies to the whole scanner, including a paused or scheduled
scan, even when querying a subset of Libraries. An unavailable scanner never
reports idle. Remote tasks marked `complete` do not count as outstanding.

Plugins can implement `emit_library_workload_idle(data)` for
`events.library_workload_idle`. It runs after the scanner returns to idle at the
end of a scan pass, including a pass with no new jobs, and after normal
post-processing removes a local task or marks a remote task complete. The
existing `events.postprocessor_complete` event retains its earlier timing.

Event data contains `library_ids` of observed idle Libraries, `reason`
(`scan_complete`, `scan_cancelled` or `task_complete`), and `workload` with the query response.
The post-processing notification checks the completed task's Library; the scan
notification checks all configured Libraries. Busy Libraries are omitted from
`library_ids`. No notification is sent if none of the checked Libraries is idle.

Notifications can repeat. Consumers should coalesce their own actions and query
their full dependency set again before starting work. Queries are observations,
not reservations: new submissions or scans can start afterward. Idle does not
mean previous tasks succeeded; consult task history for failures. These events
do not describe parent-child task relationships or signal a successful batch.
Manual queue deletion and other mutations outside normal post-processing do not
independently emit this notification.


## Selecting dependencies for a Library

The Library setting `wait_for_library_ids` is an explicit list of other Library
IDs. The frontend presents the current Library display names in a multi-select.
IDs survive a rename. The default is an empty list, meaning no dependency wait.
Settings save/read and Library export/import preserve the selection. Older
clients that omit the setting preserve its saved value. Self references, missing
Libraries and invalid IDs are rejected. If a selected Library is subsequently
deleted, a workload query fails rather than treating it as finished.

Plugins opt into this setting by reading the Library configuration and querying
that exact dependency set. An empty dependency selection must be handled as no
wait without calling the all-Libraries query with `[]`. Ordinary tasks and scan
order are unchanged. This setting does not discover child tasks or include
transitive dependencies. Select processing Libraries as well as any intake
Library that submits work to them. The query still conservatively waits for the
whole scanner to return to idle when dependencies are selected.

A plugin can request the whole scan loop or selected Libraries with
`POST /pending/rescan`, as described below. A downstream scan trigger should
avoid retriggering indefinitely on empty scan completion.


## Targeted scan requests

`POST /unmanic/api/v2/pending/rescan` accepts `{"library_ids": [2, 3]}` to
scan only those Libraries. An empty HTTP body or JSON object preserves the
existing full scan request. An explicit empty list, invalid values or unknown
IDs return HTTP 400. Library scanner enablement and API-only settings still
apply; this does not enable a disabled scanner.

Repeated targeted requests are combined. Requests made while scanning are kept
for a follow-up pass, with each requested Library scanned once in that pass.
Requests made while paused stay paused. Cancellation clears follow-up requests;
requests during cancellation are rejected. Legacy full-scan requests retain
their existing rejection while the scanner is busy.

End-of-scan idle events include `scanned_library_ids`, identifying attempted
Libraries across consecutive queued passes. A cancelled pass uses reason
`scan_cancelled`, allowing consumers to avoid starting downstream work after a
manual cancellation. Task-completion events retain their original payload.
A plugin can use an idle notification to request a targeted downstream scan,
then query its dependencies before doing the downstream work. Do not start
another scan in response to that same target's empty-scan completion.


## Library selectors in plugin settings

Plugins can declare a setting with `input_type: "library_select"` and a default
value of `[]`. The settings editor uses the same named multi-select component
and current Library list as **Wait for Libraries**, excluding the current
Library. Values are lists of native Library IDs, so names can change without
changing selections. No per-Library checkbox definitions are needed.

The selector lists all other Libraries. A plugin requesting scans must account
for the targeted scan API respecting scanner enablement and API-only settings.
Plugins remain responsible for validating and interpreting their saved lists.

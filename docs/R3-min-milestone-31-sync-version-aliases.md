# R3-min Milestone 31: LAN sync version alignment

## Scope

This milestone closes the Python-side version alias gap between AgentRuntime actor imports and LANChat sync ingestion.

## Changes

- Normalize `source_scene_version` to `scene_version` at the native LANChat bridge.
- Normalize `entity_version` to `actor_version` at the native LANChat bridge.
- Accept the same aliases when sync events enter AgentRuntime without passing through LANChatAgentWorker.
- Reject an explicitly older scene-version event for the currently mirrored remote-host plan.
- Preserve plan isolation: an event for a different plan does not replace or mutate the current peer-mirror plan.

## Verification boundary

Python tests verify alias propagation and stale-event rejection. Real host/member broadcast ordering, duplicate suppression, asset transfer, and peer Snapshot consistency remain `[待 F5/实机验证]`.

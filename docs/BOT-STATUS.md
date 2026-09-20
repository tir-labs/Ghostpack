# Discord adapter status

The initial bot implements /live, /end, reporting-thread submissions and editor-role-gated approval/hold buttons. This is NOT production-ready: thread-to-event mapping is in memory and is lost on restart; /end needs an explicit confirmation; editor feedback/revisions and private archive delivery are not implemented; attachments are currently only recorded as Discord URLs and must be ingested privately immediately; approval does not upload media or publish to Ghost. Never expose unpublished submissions to a public archive. The Discord bot needs Message Content intent enabled and channel permissions.

The keypoints helper is opt-in and only accepts explicitly published updates. It is not yet scheduled or wired to Ghost. The codebase remains a development scaffold.

# Development status

The media service is a first implementation, not a production-ready Ghost integration. Ghost Admin uploads are NOT intercepted. GhostLive bot, editorial approvals, Ghost uploads, archives, key points and theme are NOT implemented. Do not deploy for real reporting yet.

Processing is synchronous and CPU intensive; add an asynchronous job queue, concurrency quotas, file signature validation, malware scanning, disk retention, upload streaming controls, codec availability checks, metrics and retry handling. FFmpeg build must include libsvtav1 and AVIF support. Ghost acceptance and delivery of AVIF/WebM must be verified on the target Ghost installation. No Ghostpack duration limit applies to direct Ghost uploads, but a 2 GiB per-file safety cap is currently configured in this prototype.

Originals remain on disk until manually deleted; implement encrypted private storage and retention policy. Watermark only when configured. This service does not yet upload processed files into Ghost.

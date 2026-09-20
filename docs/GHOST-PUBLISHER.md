# Ghost publisher integration (development)

The Discord bot service includes a Ghost Admin JWT signer and an adapter for creating a draft, fetching a post, and appending approved text to an existing post using Ghost's HTML source conversion. These methods are not yet invoked by Discord approval buttons and have not been integration-tested with a Ghost installation. Do not assume that a Ghost draft or update was published merely because an editorial approval succeeded.

The append operation reads the current Ghost post and sends updated_at as an optimistic concurrency guard. It does not yet provide transactional exactly-once publication, an outbox, media upload, or reconciliation when the network fails after Ghost accepts a request. Ghost's editor representation and HTML conversion may change existing rich cards; test with your Ghost version before use. Avoid using this adapter on existing articles containing complex cards until compatibility is verified.

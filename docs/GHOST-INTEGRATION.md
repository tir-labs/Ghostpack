# Ghost media integration status

The media API is a separate service. Ghost's native editor does **not** automatically send uploads through it. Do not claim that a storage adapter alone intercepts every upload. The next integration milestone is to test Ghost image, media and file upload routes against a specific self-hosted Ghost version, then implement a supported adapter or an editor integration with processing state and retries.

`services/media/ghost.py` contains an initial Ghost Admin JWT signer and AVIF image upload client. The image endpoint and AVIF acceptance must be integration-tested on the target installation. Do not configure an unverified video upload endpoint: Ghost's media endpoint and hosting behavior vary by version and storage setup, and AV1 WebM support is not guaranteed. A failed upload must never be represented as published.

For long direct-to-Ghost video uploads, Ghostpack imposes no duration cap; resource, reverse proxy, disk and Ghost file limits still apply. The prototype media API currently caps each upload at 2 GiB. For production, replace synchronous transcoding with an authenticated asynchronous queue, size and codec validation, retention controls, and storage appropriate to the installation.

To run the unit test locally: `cd services/media && python -m unittest discover -s tests`.

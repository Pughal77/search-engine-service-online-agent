This is a search engine service powered by sear xng.

For deployment, it is deployed as a single pod but has 2 containers in them

Using the sidecar pattern, we talk to searxng container by creating the api, exposing that endpoint and then using 'localhost' to forward requests recieved by api to the searxng container


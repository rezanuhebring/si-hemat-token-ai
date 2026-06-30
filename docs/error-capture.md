administrator@ollama:~/si-hemat-token-ai/scripts$ sudo ./deploy-stack.sh
[+] up 34/35
 ✔ Image postgres:16                                   Pulled                                                     124.4s
 ✔ Image apache/tika:latest-full                       Pulled                                                     110.2s
 ✔ Image chromadb/chroma:1.5.2                         Pulled                                                     108.0s
 ⠏ Image ollama/ollama:latest [⣿⣿⣿⣿] 3.254GB / 3.254GB Pulling                                                    360.0s
[+] Building 135.0s (16/16) FINISHED
 => [internal] load local bake definitions                                                                         0.0s
 => => reading from stdin 1.06kB                                                                                   0.0s
 => [litellm internal] load build definition from Dockerfile                                                       3.0s
 => => transferring dockerfile: 284B                                                                               0.0s
 => [openwebui-tools internal] load build definition from Dockerfile                                               2.4s
 => => transferring dockerfile: 338B                                                                               0.0s
 => [openwebui-tools internal] load metadata for docker.io/library/python:3.12-slim                                4.2s
 => [litellm internal] load metadata for docker.litellm.ai/berriai/litellm-database:main-stable                   12.1s
 => [litellm internal] load .dockerignore                                                                          0.7s
 => => transferring context: 2B                                                                                    0.0s
 => [openwebui-tools 1/5] FROM docker.io/library/python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151d  9.2s
 => => resolve docker.io/library/python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc8  0.6s
 => => sha256:b32430367bf08f32c23778909985ac645d1794f0aeef670aa796a50c8751527d 248B / 248B                         0.8s
 => => sha256:df79d931cd67092e2b8e48d8f6369922571efe4ee0f9af71636ce36600481492 12.11MB / 12.11MB                   1.7s
 => => sha256:aff2d9f8dc87f4c10bbb7f438f3a325169379776bdfad5c49e4be5acc3c2f192 1.29MB / 1.29MB                     1.4s
 => => extracting sha256:aff2d9f8dc87f4c10bbb7f438f3a325169379776bdfad5c49e4be5acc3c2f192                          0.6s
 => => extracting sha256:df79d931cd67092e2b8e48d8f6369922571efe4ee0f9af71636ce36600481492                          1.0s
 => => extracting sha256:b32430367bf08f32c23778909985ac645d1794f0aeef670aa796a50c8751527d                          0.7s
 => [openwebui-tools internal] load build context                                                                  1.4s
 => => transferring context: 38.25kB                                                                               0.0s
 => [litellm 1/2] FROM docker.litellm.ai/berriai/litellm-database:main-stable@sha256:fc15e199e743c64beb00ac2cd6  102.9s
 => => resolve docker.litellm.ai/berriai/litellm-database:main-stable@sha256:fc15e199e743c64beb00ac2cd6ac01e48ba1  1.0s
 => => sha256:d82e7da549524aaa104d2e1bb04f225eef0909c8a3b6088f35b4ff1deb4b0f77 1.23kB / 1.23kB                     8.2s
 => => sha256:c6003eb9ed7c15d2c91b22f13d0f3202c5fd04ea9f6c014064fc892efcad9a22 60.65MB / 60.65MB                  10.8s
 => => sha256:7ecdc8fbbfd5e08439c42894b70aeb8079704be94218d20de555af9752730334 47.33MB / 47.33MB                   8.3s
 => => sha256:32baba9b25b8bd047e32e5ca49becd0ea9763178d5ea5f1e2702da84a8b4efec 3.35MB / 3.35MB                     7.1s
 => => sha256:9bd31bfdeb40c71611cbd9aa2ed41aea09440e616cf995fbac2ffeb6d6a35ae1 615B / 615B                         1.4s
 => => sha256:481f7addd8cbbd1562e1fee9daf5f7e2422fe054da90fd0b84d05997471b9b7c 11.10kB / 11.10kB                   1.4s
 => => sha256:61116b69631c1478a5e0abc3de6b2459515fd7baa7b5756b56cd65ac304178b7 4.74kB / 4.74kB                     1.8s
 => => sha256:e96360ae5db74a5eb4f3e5b5b905a2bf756de7b5f0185c48dd0886267d23c638 171.36MB / 171.36MB                25.7s
 => => sha256:9218ad69d3e14190890030bbecc83dd2fa47d085f08fba34d28ff694f10ddcd2 92B / 92B                           1.7s
 => => sha256:7b015f82577d81713689852c22fd4f921e9caba6ddd0c5d0f981e0feda6126d5 70.88MB / 70.88MB                  13.0s
 => => sha256:ab407a4aad8610bb9a0402e561dc28916d69ab9d770410708d62f30700c616fc 13.86kB / 13.86kB                   1.7s
 => => sha256:cdea145aa11554331de7d95b1834fd4f2a784fa573086475ff0d7c86d3abd020 2.87kB / 2.87kB                     2.8s
 => => sha256:5f460b97a17ec3e9d41e0f61e207b83dee4c64f0bc6eb5df13b05d005fbc9a15 11.83kB / 11.83kB                   2.0s
 => => sha256:e3e6b87d346eab63f52accb0375498d94dbe56487890b1cd5951d48adcd1ac8e 62.48kB / 62.48kB                   1.3s
 => => sha256:b7f1816b5f236acfb30211376d2d7c9dd153c13c62552bfed9e05c90a9327c5d 94.84kB / 94.84kB                   1.3s
 => => sha256:7c6e71c1fdfdf429844e25aad86441920641c0ba46466bc1d043556bfb81b24e 95.69kB / 95.69kB                   1.7s
 => => sha256:9201e51fe8c1f99c6602ba89bc6cbd3895501936ba9f62f705bb8f150d9bbace 129.66kB / 129.66kB                 1.5s
 => => sha256:1d53393b78f00c417dbc484afee224f386ba037746127e62a4bc86b6ad11daa1 172.00kB / 172.00kB                 1.9s
 => => sha256:08b1ee65ff0b2ba85d726e2903858acf73937757cd4888f925317fb5c399149d 417.37kB / 417.37kB                 1.8s
 => => sha256:b5d9209275752ec978dd1b2a23866e31ea894283ef3da8cbb133a7fb7586c0d6 3.22MB / 3.22MB                     2.6s
 => => sha256:921463509c56ecb8e6085dcc68ab9cd6fc44ecade7b7b2cbb21e1220a2ff28a7 2.83MB / 2.83MB                     2.7s
 => => extracting sha256:921463509c56ecb8e6085dcc68ab9cd6fc44ecade7b7b2cbb21e1220a2ff28a7                          1.9s
 => => extracting sha256:b5d9209275752ec978dd1b2a23866e31ea894283ef3da8cbb133a7fb7586c0d6                          2.6s
 => => extracting sha256:08b1ee65ff0b2ba85d726e2903858acf73937757cd4888f925317fb5c399149d                          1.1s
 => => extracting sha256:1d53393b78f00c417dbc484afee224f386ba037746127e62a4bc86b6ad11daa1                          2.2s
 => => extracting sha256:9201e51fe8c1f99c6602ba89bc6cbd3895501936ba9f62f705bb8f150d9bbace                          1.5s
 => => extracting sha256:7c6e71c1fdfdf429844e25aad86441920641c0ba46466bc1d043556bfb81b24e                          1.6s
 => => extracting sha256:b7f1816b5f236acfb30211376d2d7c9dd153c13c62552bfed9e05c90a9327c5d                          1.8s
 => => extracting sha256:e3e6b87d346eab63f52accb0375498d94dbe56487890b1cd5951d48adcd1ac8e                          1.0s
 => => extracting sha256:5f460b97a17ec3e9d41e0f61e207b83dee4c64f0bc6eb5df13b05d005fbc9a15                          0.7s
 => => extracting sha256:cdea145aa11554331de7d95b1834fd4f2a784fa573086475ff0d7c86d3abd020                          1.0s
 => => extracting sha256:ab407a4aad8610bb9a0402e561dc28916d69ab9d770410708d62f30700c616fc                          1.2s
 => => extracting sha256:7b015f82577d81713689852c22fd4f921e9caba6ddd0c5d0f981e0feda6126d5                          2.6s
 => => extracting sha256:9218ad69d3e14190890030bbecc83dd2fa47d085f08fba34d28ff694f10ddcd2                          1.9s
 => => extracting sha256:e96360ae5db74a5eb4f3e5b5b905a2bf756de7b5f0185c48dd0886267d23c638                          9.7s
 => => extracting sha256:61116b69631c1478a5e0abc3de6b2459515fd7baa7b5756b56cd65ac304178b7                          3.4s
 => => extracting sha256:481f7addd8cbbd1562e1fee9daf5f7e2422fe054da90fd0b84d05997471b9b7c                          6.1s
 => => extracting sha256:9bd31bfdeb40c71611cbd9aa2ed41aea09440e616cf995fbac2ffeb6d6a35ae1                          3.8s
 => => extracting sha256:32baba9b25b8bd047e32e5ca49becd0ea9763178d5ea5f1e2702da84a8b4efec                          1.2s
 => => extracting sha256:7ecdc8fbbfd5e08439c42894b70aeb8079704be94218d20de555af9752730334                          1.3s
 => => extracting sha256:c6003eb9ed7c15d2c91b22f13d0f3202c5fd04ea9f6c014064fc892efcad9a22                          1.5s
 => => extracting sha256:d82e7da549524aaa104d2e1bb04f225eef0909c8a3b6088f35b4ff1deb4b0f77                          1.4s
 => [openwebui-tools 2/5] WORKDIR /app                                                                             3.6s
 => [openwebui-tools 3/5] COPY tools/requirements.txt /tmp/requirements.txt                                        3.6s
 => [openwebui-tools 4/5] RUN pip install --no-cache-dir -r /tmp/requirements.txt                                 20.3s
 => [openwebui-tools 5/5] COPY tools/app /app                                                                     10.3s
 => [openwebui-tools] exporting to image                                                                          29.7s
 => => exporting layers                                                                                           17.4s
 => => exporting manifest sha256:fd63b6261f9c413e361380beaed62ce2eef45bb975527eae3b29bd5124da2d47                  2.4s
 => => exporting config sha256:9081c2f08d775b9408dfb7a789de9479e3add9d0b73f94c7aefd3d99d928ed41                    1.0s
 => => exporting attestation manifest sha256:e79ae9d57c89bab14ff22921473224a0e9c6c93c4a2f913aaf6052275be48ab3      2.3s
 => => exporting manifest list sha256:ee0567260bce60f2294c110167ef34441a71ccba0a727118e50b6f4dddf8acf6             1.0s
 => => naming to docker.io/library/si-hemat-token-ai-openwebui-tools:latest                                        0.2s
 => => unpacking to docker.io/library/si-hemat-token-ai-openwebui-tools:latest                                     4.2s
 => [openwebui-tools] resolving provenance for metadata file                                                       0.0s
 => ERROR [litellm 2/2] RUN apk add --no-cache py3-pip  && pip install --no-cache-dir --target /app/.venv/lib/pyt  5.2s
[+] up 35/37
 ✔ Image postgres:16                       Pulled                                                                 124.4s
 ✔ Image apache/tika:latest-full           Pulled                                                                 110.2s
 ✔ Image chromadb/chroma:1.5.2             Pulled                                                                 108.0s
 ✔ Image ollama/ollama:latest              Pulled                                                                 360.0s
 ⠙ Image si-hemat-token-ai-openwebui-tools Building                                                               138.6s
 ⠙ Image litellm-with-pillow:local         Building                                                               138.6s
WARNING: current commit information was not captured by the build: failed to read current commit information with git rev-parse --is-inside-work-tree

WARNING: current commit information was not captured by the build: failed to read current commit information with git rev-parse --is-inside-work-tree

Dockerfile:4

--------------------

   3 |     # Pillow is required by LiteLLM's Ollama image conversion path.

   4 | >>> RUN apk add --no-cache py3-pip \

   5 | >>>      && pip install --no-cache-dir --target /app/.venv/lib/python3.13/site-packages Pillow

   6 |

--------------------

target litellm: failed to solve: process "/bin/sh -c apk add --no-cache py3-pip \t&& pip install --no-cache-dir --target /app/.venv/lib/python3.13/site-packages Pillow" did not complete successfully: exit code: 127
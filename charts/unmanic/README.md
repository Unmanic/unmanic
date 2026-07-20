# Unmanic Helm Chart

Deploys [Unmanic](https://docs.unmanic.app/) — a plugin-driven library
optimiser — on Kubernetes. Designed for GitOps/ArgoCD: no Helm hooks,
deterministic rendering, pinned image tags, and prune-protected state.

## Scope and the singleton constraint

Unmanic stores everything (settings, task queue, plugins, logs) in a
single-writer SQLite database under `/config`. Therefore:

- **One release = one instance = one replica.** The chart hard-fails on
  `replicaCount > 1` and uses `strategy: Recreate`.
- Scale out by installing the chart multiple times and federating the
  instances with Unmanic **installation links** (see [Federation](#federation)).

## Quickstart

```bash
helm install unmanic ./charts/unmanic \
  --namespace media --create-namespace \
  --set libraries[0].name=library \
  --set libraries[0].mountPath=/library \
  --set libraries[0].existingClaim=media-library
```

Then port-forward or enable the ingress and open the web UI. Workers, plugins
and libraries are configured in the UI (Settings).

## ArgoCD

See [`examples/argocd-application.yaml`](examples/argocd-application.yaml) and
[`examples/argocd-applicationset-federation.yaml`](examples/argocd-applicationset-federation.yaml).

- **No hooks.** The app migrates its own database on boot; there are no
  pre/post-sync jobs.
- **Deterministic manifests.** Map iteration is sorted; nothing random is
  rendered. Repeated `helm template` runs are byte-identical, so ArgoCD shows
  no phantom drift.
- **Config-change restarts.** A `checksum/config` pod annotation covers every
  value feeding the container environment; changing one rolls the pod on sync.
- **State protection.** The chart-created config PVC carries
  `helm.sh/resource-policy: keep` and `argocd.argoproj.io/sync-options: Prune=false`.
- **Pin image tags.** `image.tag` defaults to the chart `appVersion`; never
  set it to `latest` under ArgoCD.

## Declarative configuration limits

Values under `config:` (and `configSecret:`) are injected as environment
variables named after Unmanic's lowercase setting keys (`ui_port`,
`library_path`, `enable_library_scanner`, `installation_name`, …).

Unmanic's precedence is: *defaults < environment variables <
`/config/settings.json`*. The web UI writes `settings.json` when you save
settings, so **any key ever saved via the UI permanently overrides the env
var**. Treat `config:` as first-boot bootstrap plus best-effort declarative
config, and be aware that UI-managed state (worker groups, libraries, plugins,
installation links) lives only in the database/settings file — it cannot be
fully managed from values.

Special keys the chart understands and keeps consistent everywhere:

- `config.ui_port` — also updates the container port, probes and NetworkPolicy.
- `config.cache_path` — also moves the cache volume mount.

## Storage

| Mount | Purpose | Default |
|---|---|---|
| `/config` | settings.json, SQLite DB, plugins, logs, userdata | chart-created 2Gi PVC (prune-protected) |
| `/tmp/unmanic` | in-progress encode scratch, wiped at startup | emptyDir, 20Gi sizeLimit |
| libraries | your media | placeholder emptyDir until you set a source |

### Config

```yaml
persistence:
  config:
    existingClaim: my-unmanic-config   # or let the chart create one
```

### Cache

Size it to at least `largest_file_size x 2 x worker_count` (each worker holds
an input and an output copy). Options:

```yaml
persistence:
  cache:
    type: emptyDir   # node disk (default)
    # type: memory   # tmpfs — fast, counts against the pod memory limit
    # type: pvc      # dedicated volume; set size/storageClass or existingClaim
    sizeLimit: 20Gi
```

### Libraries

Each entry becomes a volume + mount; give each **at most one** source:

```yaml
libraries:
  - name: movies
    mountPath: /library/movies
    existingClaim: media-movies        # any PVC, incl. NFS/CIFS via CSI
  - name: tv
    mountPath: /library/tv
    nfs: {server: nas.lan, path: /volume1/tv}
  - name: music
    mountPath: /library/music
    hostPath: /mnt/music
    readOnly: true
```

For CIFS/SMB shares use the [SMB CSI driver](https://github.com/kubernetes-csi/csi-driver-smb)
and reference the resulting PVC with `existingClaim`. Anything else fits
through `extraVolumes` / `extraVolumeMounts`.

## GPU transcoding

Hardware acceleration is used by plugins (e.g. Transcode Video); the core app
does not require it. Presets:

```yaml
gpu:
  mode: nvidia   # none | nvidia | intel | amd | custom
```

- **nvidia** — requires the NVIDIA device plugin / gpu-operator. Sets
  `runtimeClassName: nvidia` (disable with `gpu.nvidia.useRuntimeClass=false`),
  an `nvidia.com/gpu` limit (disable with `useResourceLimit=false`),
  `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES=compute,video,utility`
  and optionally `NVIDIA_PATCH_VERSION` (keylase NVENC session-limit patch).
- **intel** — requires the [Intel GPU device plugin](https://github.com/intel/intel-device-plugins-for-kubernetes)
  (typically with Node Feature Discovery). Requests `gpu.intel.com/i915`, adds
  `supplementalGroups: [44, 109]` (video/render) and, when
  `nodeAffinityLabel` is set, a required node affinity. Optional
  `LIBVA_DRIVER_NAME` (e.g. `iHD`).
- **amd** — requests `amd.com/gpu` via the AMD device plugin, or set
  `gpu.amd.useHostPath=true` to mount `/dev/dri` straight from the host.
  Also adds the video/render supplemental groups.
- **custom** — chart adds nothing; wire your own `resources`, `extraEnv`,
  `extraVolumes`.

## Rootless mode

```yaml
rootless:
  enabled: true
  runAsUser: 568
  runAsGroup: 568
  fsGroup: 568
```

Sets the pod securityContext and `HOME=/config` (required by Unmanic), and
omits `PUID`/`PGID`. **Caveat:** plugins that install apt packages at runtime
will fail without root. Default mode instead starts as root and drops to
`puid`/`pgid` via gosu (the image's stock behaviour).

## Exposing the UI

Unmanic serves the web UI, REST API and a websocket
(`/unmanic/websocket`) on a single port (8888) and **has no built-in
authentication**. Front it with an authenticating proxy (ingress basic-auth
annotations, oauth2-proxy, Authelia, …) before exposing it beyond a trusted
network.

Reverse-proxy requirements:

- Unmanic must be served at the **root path of a host** — there is no
  base-URL/subpath support.
- Websocket upgrades must pass through.
- Allow effectively unlimited request bodies — linked installations transfer
  whole media files over HTTP. For ingress-nginx:

```yaml
ingress:
  enabled: true
  className: nginx
  host: unmanic.example.com
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
```

Gateway API users can enable `httpRoute` instead (body-size/websocket handling
is then the Gateway's concern).

### In-app SSL

```yaml
ssl:
  enabled: true
  existingSecret: unmanic-tls   # kubernetes.io/tls secret
```

Port 8888 then serves HTTPS directly and the probes switch scheme
automatically. Most clusters terminate TLS at the ingress instead.

## Federation

To use more than one machine/GPU, deploy several releases and link them:

1. Install N releases (see the ApplicationSet example), each with a distinct
   `fullnameOverride`, its own config PVC, and:

   ```yaml
   config:
     installation_name: "unmanic-worker-1"
     installation_public_address: "http://unmanic-worker-1.media.svc.cluster.local:8888"
     # optional: distributed_worker_count_target: "5"
   ```

2. Mount the same RWX media storage (NFS etc.) in every instance. If both
   sides resolve the same underlying storage, linked tasks are read directly
   from disk instead of being transferred over HTTP.
3. In the main instance's web UI (Settings → Link), add each worker by its
   service address and enable send/receive. Link state lives in each
   instance's database, so this step is by design not declarative.
4. Task routing between linked installs matches on **library name** — create
   identically named libraries on every instance that should process them.
5. If instances live in different namespaces and NetworkPolicy is enabled,
   allow peer traffic on the UI port via `networkPolicy.ingressRules`.

## Values

See [`values.yaml`](values.yaml) — every key is documented inline — and
[`values.schema.json`](values.schema.json) for validation. The `ci/`
directory contains a ready-made values file per scenario (default, rootless,
nvidia/intel/amd GPU, ingress, in-app SSL, multi-library kitchen sink).
